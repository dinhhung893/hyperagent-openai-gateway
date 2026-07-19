"""FastAPI application exposing the OpenAI-compatible surface."""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from . import __version__, fallbacks, media
from .auth import Policy, verify_key
from .config import Settings, settings as default_settings
from .errors import OAIError, error_body, not_implemented
from .identities import IdentityStore
from .schemas import (ChatCompletionRequest, CompletionRequest, EmbeddingRequest,
                      ImagesRequest, ModerationRequest, ResponsesRequest, SpeechRequest)
from .state import Store
from .streaming import chat_completion_stream, responses_stream
from .toolbridge import (build_exec_directive, catalog, directive_from_tool_choice,
                         forced_tool_name, primary_param)
from .translate import (build_chat_completion, extract_file_ids, flatten_messages,
                        flatten_snapshot, latest_user_text, model_object)
from .upstream.manager import UpstreamManager


def create_app(settings: Optional[Settings] = None, adapter=None) -> FastAPI:
    settings = settings or default_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.identities = IdentityStore(settings)
        app.state.manager = UpstreamManager(settings, injected=adapter)
        app.state.store = Store(settings.state_path if adapter is None else ":memory:")
        yield
        await app.state.manager.aclose()
        app.state.store.close()

    app = FastAPI(title="Hyperagent OpenAI Gateway", version=__version__, lifespan=lifespan)

    @app.exception_handler(OAIError)
    async def _oai(_: Request, exc: OAIError):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        return JSONResponse(status_code=500,
                            content=error_body(str(exc), type_="server_error", code="internal_error"))

    def pol(request: Request) -> Policy:
        return verify_key(request, settings, request.app.state.identities)

    def ctx(request: Request, p: Policy):
        """(adapter, resolver) bound to the caller's identity."""
        mgr = request.app.state.manager
        return mgr.adapter_for(p.identity), mgr.resolver_for(p.identity)

    # --- health ------------------------------------------------------------- #
    @app.get("/v1/health")
    @app.get("/healthz")
    async def health():
        return {"status": "ok", "version": __version__, "upstream": settings.upstream}

    # --- models ------------------------------------------------------------- #
    @app.get("/v1/models")
    async def list_models(request: Request, p: Policy = Depends(pol)):
        _, resolver = ctx(request, p)
        agents = await resolver.agents(force=True)
        return {"object": "list", "data": [model_object(a) for a in agents]}

    @app.get("/v1/models/{model_id}")
    async def get_model(model_id: str, request: Request, p: Policy = Depends(pol)):
        _, resolver = ctx(request, p)
        for a in await resolver.agents():
            if a.id == model_id or a.name == model_id:
                return model_object(a)
        raise OAIError(404, f"Model '{model_id}' not found.", param="model", code="model_not_found")

    # --- tool catalog (bridge) --------------------------------------------- #
    @app.get("/v1/tools")
    async def list_tools(p: Policy = Depends(pol)):
        return {"object": "list", "data": catalog(disabled=p.disabled_tools)}

    # --- chat completions --------------------------------------------------- #
    @app.post("/v1/chat/completions")
    async def chat_completions(body: ChatCompletionRequest, request: Request,
                               p: Policy = Depends(pol)):
        adapter, resolver = ctx(request, p)
        store = request.app.state.store
        agent_id = await resolver.resolve(body.model)

        # Mode C: a client forced a canonical Hyperagent tool
        forced = forced_tool_name(body.tool_choice)
        if forced:
            if forced in p.disabled_tools:
                raise OAIError(400, f"Tool '{forced}' is disabled for this key.",
                               param="tool_choice", code="tool_disabled")
            args = _extract_tool_args(body, forced)
            if settings.exec_mode == "auto":
                snap = await _run(adapter, agent_id, build_exec_directive(forced, args))
                return build_chat_completion(body.model, snap)
            return _tool_call_completion(body.model, forced, args)

        # Stateless: OpenAI chat clients resend the full history each call, so we
        # flatten all of it into one self-contained thread (no reliance on any
        # upstream cross-turn memory).
        file_ids = extract_file_ids(body.messages) or None
        prompt = flatten_messages(body.messages)
        prompt += directive_from_tool_choice(body.tool_choice, body.tools)

        if body.stream:
            opts = body.stream_options or {}
            gen = chat_completion_stream(
                adapter, model=body.model, agent_id=agent_id, message=prompt,
                thread_id=None, file_ids=file_ids, poll_interval=settings.poll_interval,
                timeout=settings.run_timeout, include_usage=bool(opts.get("include_usage")))
            return StreamingResponse(gen, media_type="text/event-stream")

        snap = await _run(adapter, agent_id, prompt, file_ids=file_ids)
        return build_chat_completion(body.model, snap)

    # --- legacy completions ------------------------------------------------- #
    @app.post("/v1/completions")
    async def completions(body: CompletionRequest, request: Request, p: Policy = Depends(pol)):
        adapter, resolver = ctx(request, p)
        agent_id = await resolver.resolve(body.model)
        prompt = body.prompt if isinstance(body.prompt, str) else "\n".join(body.prompt)
        snap = await _run(adapter, agent_id, prompt)
        text = snap.last_assistant.content if snap.last_assistant else ""
        return {
            "id": "cmpl-" + uuid.uuid4().hex[:24], "object": "text_completion",
            "created": int(time.time()), "model": body.model,
            "choices": [{"index": 0, "text": text, "finish_reason": "stop", "logprobs": None}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    # --- responses API ------------------------------------------------------ #
    @app.post("/v1/responses")
    async def responses(body: ResponsesRequest, request: Request, p: Policy = Depends(pol)):
        adapter, resolver = ctx(request, p)
        store = request.app.state.store
        agent_id = await resolver.resolve(body.model)

        if isinstance(body.input, str):
            prompt = body.input
        elif isinstance(body.input, list):
            from .schemas import ChatMessage
            prompt = flatten_messages([ChatMessage(**m) if isinstance(m, dict) else m
                                       for m in body.input])
        else:
            prompt = ""
        if body.instructions:
            prompt = f"{body.instructions}\n\n{prompt}"
        prompt += directive_from_tool_choice(body.tool_choice, body.tools)

        # Stateful chain: reconstruct prior context from the previous response's
        # thread and prepend it (self-contained; no reliance on upstream memory).
        if body.previous_response_id:
            rec = store.get_response(body.previous_response_id)
            if rec:
                prev = await adapter.get_thread(rec["thread_id"])
                prior = flatten_snapshot(prev)
                if prior:
                    prompt = f"Prior conversation:\n{prior}\n\nNew request:\n{prompt}"

        rid = "resp_" + uuid.uuid4().hex[:24]
        thread_id = await adapter.create_thread(agent_id, prompt)  # fresh, self-contained
        store.put_response(rid, thread_id, body.model, "in_progress", {"metadata": body.metadata})

        if body.stream:
            gen = responses_stream(adapter, model=body.model, rid=rid, thread_id=thread_id,
                                   baseline=0, poll_interval=settings.poll_interval,
                                   timeout=settings.run_timeout)
            return StreamingResponse(gen, media_type="text/event-stream")

        if body.background:
            return _response_object(rid, body.model, "in_progress", "")

        snap = await adapter.wait_for_new_assistant(thread_id, 0,
                                                    poll_interval=settings.poll_interval,
                                                    timeout=settings.run_timeout)
        store.put_response(rid, thread_id, body.model, "completed", {})
        text = snap.last_assistant.content if snap.last_assistant else ""
        return _response_object(rid, body.model, "completed", text)

    @app.get("/v1/responses/{rid}")
    async def get_response(rid: str, request: Request, p: Policy = Depends(pol)):
        adapter, _ = ctx(request, p)
        store = request.app.state.store
        rec = store.get_response(rid)
        if not rec:
            raise OAIError(404, f"Response '{rid}' not found.", code="not_found")
        if rec["status"] == "cancelled":
            return _response_object(rid, rec["model"], "cancelled", "")
        snap = await adapter.get_thread(rec["thread_id"])
        status = "in_progress" if snap.running else "completed"
        if status != rec["status"]:
            store.put_response(rid, rec["thread_id"], rec["model"], status, rec["meta"])
        text = snap.last_assistant.content if (snap.last_assistant and not snap.running) else ""
        return _response_object(rid, rec["model"], status, text)

    @app.post("/v1/responses/{rid}/cancel")
    async def cancel_response(rid: str, request: Request, p: Policy = Depends(pol)):
        store = request.app.state.store
        rec = store.get_response(rid)
        if not rec:
            raise OAIError(404, f"Response '{rid}' not found.", code="not_found")
        # Upstream has no cancel tool; mark cancelled locally (best-effort, documented).
        store.put_response(rid, rec["thread_id"], rec["model"], "cancelled", rec["meta"])
        return _response_object(rid, rec["model"], "cancelled", "")

    @app.get("/v1/responses/{rid}/input_items")
    async def response_input_items(rid: str, request: Request, p: Policy = Depends(pol)):
        adapter, _ = ctx(request, p)
        store = request.app.state.store
        rec = store.get_response(rid)
        if not rec:
            raise OAIError(404, f"Response '{rid}' not found.", code="not_found")
        snap = await adapter.get_thread(rec["thread_id"])
        items = [{
            "id": "msg_" + uuid.uuid4().hex[:16], "type": "message", "role": m.role,
            "content": [{"type": "input_text", "text": m.content}],
        } for m in snap.messages if m.role in ("user", "system")]
        return {"object": "list", "data": items, "has_more": False}

    # --- files (E09) -------------------------------------------------------- #
    @app.post("/v1/files")
    async def upload_file(request: Request, p: Policy = Depends(pol)):
        adapter, _ = ctx(request, p)
        store = request.app.state.store
        form = await request.form()
        up = form.get("file")
        purpose = str(form.get("purpose", "assistants"))
        if up is None:
            raise OAIError(400, "Missing 'file'.", param="file")
        data = await up.read()
        info = await adapter.create_attachment_upload(
            filename=up.filename or "upload.bin",
            content_type=up.content_type or "application/octet-stream", size=len(data))
        fid = info.get("fileId") or ("file_" + uuid.uuid4().hex[:12])
        upload_url = info.get("uploadUrl")
        if upload_url and not upload_url.startswith("https://mock.upload/"):
            import httpx
            async with httpx.AsyncClient() as c:
                await c.put(upload_url, content=data,
                            headers={"Content-Type": up.content_type or "application/octet-stream"})
        store.put_file(fid, up.filename or "upload.bin", len(data), purpose,
                       created=int(time.time()), content=data)
        return _file_object(store.get_file(fid))

    @app.get("/v1/files")
    async def list_files(request: Request, p: Policy = Depends(pol)):
        store = request.app.state.store
        return {"object": "list", "data": [_file_object(f) for f in store.list_files()]}

    @app.get("/v1/files/{fid}")
    async def get_file(fid: str, request: Request, p: Policy = Depends(pol)):
        rec = request.app.state.store.get_file(fid)
        if not rec:
            raise OAIError(404, f"File '{fid}' not found.", code="not_found")
        return _file_object(rec)

    @app.get("/v1/files/{fid}/content")
    async def get_file_content(fid: str, request: Request, p: Policy = Depends(pol)):
        content = request.app.state.store.get_file_content(fid)
        if content is None:
            raise OAIError(404, f"Content for file '{fid}' is not retained by the gateway.",
                           code="not_found")
        return Response(content=content, media_type="application/octet-stream")

    @app.delete("/v1/files/{fid}")
    async def delete_file(fid: str, request: Request, p: Policy = Depends(pol)):
        ok = request.app.state.store.delete_file(fid)
        if not ok:
            raise OAIError(404, f"File '{fid}' not found.", code="not_found")
        return {"id": fid, "object": "file", "deleted": True}

    # --- embeddings & moderations (E11 fallbacks) --------------------------- #
    @app.post("/v1/embeddings")
    async def embeddings(body: EmbeddingRequest, p: Policy = Depends(pol)):
        if settings.embeddings_mode == "off":
            raise not_implemented("Embeddings", "Set GATEWAY_EMBEDDINGS=fallback or wire a provider/skill.")
        inputs = fallbacks.normalize_inputs(body.input)
        return fallbacks.embeddings_response(body.model, inputs, settings.embeddings_dim)

    @app.post("/v1/moderations")
    async def moderations(body: ModerationRequest, p: Policy = Depends(pol)):
        inputs = fallbacks.normalize_inputs(body.input)
        return fallbacks.moderations_response(body.model or "", inputs)

    # --- media: images & audio (E08) --------------------------------------- #
    @app.post("/v1/images/generations")
    async def images_generations(body: ImagesRequest, request: Request, p: Policy = Depends(pol)):
        adapter, resolver = ctx(request, p)
        agent_id = await resolver.resolve(body.model or "hyperagent-default")
        snap = await _run(adapter, agent_id,
                          f"[Directive] Generate an image: {body.prompt}. {media.PUBLISH_HINT}")
        return _media_urls_or_502(snap, "image", revised=body.prompt, n=body.n or 1)

    @app.post("/v1/images/edits")
    async def images_edits(request: Request, p: Policy = Depends(pol)):
        adapter, resolver = ctx(request, p)
        prompt, model = "", None
        if request.headers.get("content-type", "").startswith("multipart/"):
            form = await request.form()
            prompt, model = str(form.get("prompt", "")), form.get("model")
        else:
            data = await request.json()
            prompt, model = data.get("prompt", ""), data.get("model")
        agent_id = await resolver.resolve(model or "hyperagent-default")
        snap = await _run(adapter, agent_id,
                          f"[Directive] Edit/generate an image: {prompt}. {media.PUBLISH_HINT}")
        return _media_urls_or_502(snap, "image", revised=prompt, n=1)

    @app.post("/v1/audio/speech")
    async def audio_speech(body: SpeechRequest, request: Request, p: Policy = Depends(pol)):
        adapter, resolver = ctx(request, p)
        agent_id = await resolver.resolve(body.model or "hyperagent-default")
        voice = f" using voice '{body.voice}'" if body.voice else ""
        snap = await _run(adapter, agent_id,
                          f"[Directive] Generate audio (text-to-speech){voice}: "
                          f"{body.input}. {media.PUBLISH_HINT}")
        text = snap.last_assistant.content if snap.last_assistant else ""
        url = media.first_url(text)
        if not url:
            arts = media.extract_artifacts(text)
            raise OAIError(502, "Upstream returned no fetchable audio URL"
                           + (f" (artifact {arts[0]} not externally resolvable)" if arts else "")
                           + ".", type_="server_error", code="no_artifact")
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.get(url)
                r.raise_for_status()
            fmt = (body.response_format or "mp3").lower()
            ctype = {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/opus",
                     "aac": "audio/aac", "flac": "audio/flac", "pcm": "audio/L16"}.get(
                        fmt, "application/octet-stream")
            return Response(content=r.content, media_type=ctype)
        except Exception:
            return media.speech_url_response(url, body.model or "")

    @app.post("/v1/audio/transcriptions")
    async def audio_transcriptions(request: Request, p: Policy = Depends(pol)):
        return media.transcription_response(await _transcribe(request, p, translate=False))

    @app.post("/v1/audio/translations")
    async def audio_translations(request: Request, p: Policy = Depends(pol)):
        return media.transcription_response(await _transcribe(request, p, translate=True))

    async def _transcribe(request: Request, p: Policy, translate: bool) -> str:
        adapter, resolver = ctx(request, p)
        form = await request.form()
        up = form.get("file")
        model = form.get("model")
        if up is None:
            raise OAIError(400, "Missing 'file'.", param="file")
        data = await up.read()
        info = await adapter.create_attachment_upload(
            filename=up.filename or "audio", content_type=up.content_type or "application/octet-stream",
            size=len(data))
        fid = info.get("fileId")
        upl = info.get("uploadUrl")
        if upl and not upl.startswith("https://mock.upload/"):
            import httpx
            async with httpx.AsyncClient() as c:
                await c.put(upl, content=data,
                            headers={"Content-Type": up.content_type or "application/octet-stream"})
        verb = "Transcribe and translate to English" if translate else "Transcribe"
        agent_id = await resolver.resolve(model or "hyperagent-default")
        snap = await _run(adapter, agent_id,
                          f"[Directive] {verb} the attached audio. Reply with only the resulting text.",
                          file_ids=[fid] if fid else None)
        return snap.last_assistant.content if snap.last_assistant else ""

    # shared upstream run helper (maps TimeoutError -> OpenAI 504)
    async def _run(adapter, agent_id, message, thread_id=None, file_ids=None):
        try:
            return await adapter.run_sync(
                agent_id=agent_id, message=message, thread_id=thread_id, file_ids=file_ids,
                poll_interval=settings.poll_interval, timeout=settings.run_timeout)
        except TimeoutError as e:
            raise OAIError(504, str(e), type_="server_error", code="upstream_timeout")

    return app


# --------------------------- module-level helpers --------------------------- #
def _file_object(rec: dict) -> dict:
    return {"id": rec["id"], "object": "file", "bytes": rec["bytes"],
            "created_at": rec.get("created", 0), "filename": rec["filename"],
            "purpose": rec["purpose"]}


def _media_urls_or_502(snap, kind: str, revised: str, n: int):
    text = snap.last_assistant.content if snap.last_assistant else ""
    urls = media.extract_urls(text)
    if urls:
        return media.images_response(urls[:n], revised_prompt=revised)
    arts = media.extract_artifacts(text)
    hint = (f" (agent returned artifact {arts[0]}, not externally fetchable; the "
            "publish-public directive should yield a URL)" if arts else "")
    raise OAIError(502, f"Upstream returned no fetchable {kind} URL{hint}.",
                   type_="server_error", code="no_artifact")


def _extract_tool_args(body, tool_name: str) -> dict:
    import json as _json
    for m in reversed(body.messages):
        for tc in (m.tool_calls or []):
            fn = tc.get("function", {})
            if fn.get("name") == tool_name and fn.get("arguments"):
                a = fn["arguments"]
                if isinstance(a, str):
                    try:
                        return _json.loads(a)
                    except Exception:
                        return {primary_param(tool_name): a}
                if isinstance(a, dict):
                    return a
    return {primary_param(tool_name): latest_user_text(body.messages)}


def _tool_call_completion(model: str, tool_name: str, arguments: dict) -> dict:
    import json as _json
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:24], "object": "chat.completion",
        "created": int(time.time()), "model": model,
        "system_fingerprint": "hyperagent-toolrunner",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call_" + uuid.uuid4().hex[:8], "type": "function",
                "function": {"name": tool_name, "arguments": _json.dumps(arguments)}}]},
            "finish_reason": "tool_calls"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _response_object(rid: str, model: str, status: str, text: str) -> dict:
    output = []
    if status == "completed":
        output = [{
            "type": "message", "id": "msg_" + uuid.uuid4().hex[:20], "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}]}]
    return {
        "id": rid, "object": "response", "created_at": int(time.time()),
        "status": status, "model": model, "output": output,
        "output_text": text if status == "completed" else None,
        "usage": None, "metadata": {},
    }


app = create_app()
