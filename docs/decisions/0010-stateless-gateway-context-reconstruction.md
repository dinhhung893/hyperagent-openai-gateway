# 0010 Stateless Gateway With Context Reconstruction

Date: 2026-07-19

## Status

Accepted

## Context

Live testing (2026-07-19) showed Hyperagent MCP threads do **not** reliably carry
prior-turn context into a follow-up `send_message` run: a second turn on the same
thread did not recall a fact stated in the first turn. Two additional races were
found: after `send_message`, `get_thread` can briefly report `isRunning=false`
before the queued turn starts, yielding the *previous* assistant message (stale
reply).

## Decision

The gateway never relies on upstream cross-turn memory. Every upstream turn is a
**fresh, self-contained thread**:

1. **Chat Completions is stateless.** OpenAI clients resend the full `messages[]`
   each call, so the gateway flattens the entire history into one new thread per
   request. (A new threadId per call is expected.)
2. **Responses API reconstructs context.** For `previous_response_id`, the gateway
   reads the prior response's thread via `get_thread`, flattens it, and prepends it
   ("Prior conversation … New request …") to a new self-contained thread.
3. **New-reply detection.** Waiting for a turn now requires a NEW assistant message
   beyond a captured baseline count (`wait_for_new_assistant`), eliminating the
   stale-reply race. Streaming applies the same baseline so only the new reply is
   emitted.

## Alternatives Considered

1. Rely on upstream thread memory + reuse threads — rejected: live-unreliable.
2. Reuse the thread but also resend full context — rejected: duplicates history in
   the thread and still hit the start race.

## Consequences

Positive:
- Correct multi-turn recall regardless of upstream memory behavior; verified live
  (Responses chain recalled a code across turns).
- No stale replies.

Tradeoffs:
- No cross-call artifact/thread continuity for chat (acceptable — OpenAI chat is
  stateless by contract).
- Reconstructed Responses prompts grow with conversation length (bounded by client
  usage; can be truncated later if needed).

## Follow-Up

- Optional: cap reconstructed-context length for very long Responses chains.
