"""Helpers for media endpoints (images/audio) — artifact URL extraction and
OpenAI-shaped response builders. Hyperagent produces artifacts (URLs), not raw
byte streams, so image/audio results are surfaced as artifact URLs.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Optional

URL_RE = re.compile(r'https?://[^\s)\]}"\'<>]+')
# Hyperagent artifact placeholder, e.g. [[IMAGE_ntreiv4a]] / [[AUDIO_xx]] / [[FILE_xx]]
ARTIFACT_RE = re.compile(r'\[\[([A-Z]+)_([A-Za-z0-9]+)\]\]')

# Directive suffix that makes the agent return an externally fetchable URL.
# Live-verified 2026-07-19: publishing publicly yields a pub.hyperagent.com URL
# that returns real image/audio bytes (200), unlike the auth-gated artifact token.
PUBLISH_HINT = ("Then publish the file publicly and reply with ONLY the public "
                "https URL — no markdown, no artifact placeholder, no other text.")


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def extract_artifacts(text: str) -> list[str]:
    """Return Hyperagent artifact placeholders (TYPE_id) present in text."""
    return [f"{t}_{i}" for t, i in ARTIFACT_RE.findall(text or "")]


def first_url(text: str) -> Optional[str]:
    urls = extract_urls(text)
    return urls[0] if urls else None


def images_response(urls: list[str], revised_prompt: Optional[str] = None) -> dict:
    data = []
    for u in urls:
        item = {"url": u}
        if revised_prompt:
            item["revised_prompt"] = revised_prompt
        data.append(item)
    return {"created": int(time.time()), "data": data}


def transcription_response(text: str) -> dict:
    return {"text": text}


def speech_url_response(url: str, model: str) -> dict:
    # Documented deviation: OpenAI returns raw audio bytes; when the upstream
    # yields an artifact URL that cannot be byte-fetched, we return JSON with the
    # artifact URL instead. Real, fetchable URLs are streamed as bytes (see app).
    return {"object": "audio.speech", "model": model, "url": url,
            "note": "Hyperagent audio artifact URL; fetch it to obtain bytes."}
