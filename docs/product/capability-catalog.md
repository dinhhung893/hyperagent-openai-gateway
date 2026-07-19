# Hyperagent Capability Catalog (complete)

Every capability a Hyperagent agent can use inside a thread, sourced from
`hyperagent.com/docs/reference/available-tools` and the Concepts pages
(2026-07-19). These are **agent-internal tools** — not directly callable over
MCP — so the gateway exposes them two ways (see `tool-bridge.md`): as observable
`tool_calls` in responses, and as directable OpenAI functions.

Names are the docs' product names; exact runtime parameter schemas are validated
at build time. Confidence noted where the docs are capability-level only.

## 1. Search & research
- **Web Search (Exa)** — semantic/keyword web search; filter by domain, date,
  content type. Out: URLs (+ optional page content).
- **Web Contents (Exa)** — fetch & parse clean content from URL(s); highlights,
  summaries, livecrawl.
- **Image Search** — search web images; Out: image URLs + metadata.

## 2. Browser automation (capability-level in public docs)
- **Browser** — open a live browser, navigate, observe, extract content,
  screenshot, scroll, click/type, upload, back/forward/refresh, wait. Granular
  sub-actions are real in runtime; docs describe them at capability level.

## 3. Code, compute & filesystem  ← "Shell / Write / filesystem" live here
- **Code Execution (Bash / Shell)** — run bash in a sandbox; Python, Node.js,
  standard CLI; **working directory persists** across commands.
- **Filesystem** — read, write, edit files; list/glob/grep; subsumed under the
  sandbox. (Read / Write / Edit / LS / Glob / Grep.)
- **File Management** — save a sandbox file to an artifact, publish a public URL,
  fetch stored files, manage lifecycle.

## 4. Media generation & audio
- **Image Generation** — Gemini Flash, Gemini Pro, GPT Image 2; input images for
  editing; aspect ratios; up to 4K.
- **Video Generation** — Veo; 4–8s clips, native audio; first-frame + reference
  images for consistency; extend clips.
- **Audio Generation (TTS)** — 30 voices; single or multi-speaker dialogue.
- **Avatar Video (HeyGen)** — talking-head; stock or custom avatars/voices.
- **Audio Transcription** — diarization, timestamps, emotion; MP3/M4A/WAV/OGG/FLAC/AAC.

## 5. Structured artifacts
- **Documents** — persistent, sectioned, versioned; scope thread/project/global;
  append/prepend/replace/restructure.
- **Tables** — typed columns (text/number/date/url/boolean); rows + cell updates;
  export CSV/JSON.
- **Webpages** — publish self-contained HTML artifacts; edit/republish at a URL.
- **Slides** — decks with navigation/keyboard/touch.
- **Maps** — interactive HTML map artifacts (see family 6).
- **HyperApps** — interactive apps that can search the web, query tables, spawn
  agents, fetch live data; each gets a URL. (Build params capability-level.)

## 6. Location intelligence
- **Map Generation** — markers (color/glyph/popup) + route polylines; styles
  streets/satellite/terrain/dark.
- **Geocoding** — address ↔ coordinates.
- **Directions** — driving/walking/bicycling/transit; distance, duration, polyline.
- **Distance Matrix** — many origins × destinations.
- **Place Search** — POIs near a location; type/rating/open filters.
- **Street View** — static image or interactive 360° panorama.
- **Weather** — current; hourly ≤240h; daily ≤10d.
- **Time Zone** — UTC offset + DST.
- **Aerial View** — 3D cinematic aerial video (US addresses only).

## 7. Knowledge (skills, memories, rubrics)
- **Skills** — reusable methods; loading modes pinned/available/discoverable;
  **Skill Scripts** (fetch into workspace) and **Credential Injection** (run with
  a skill's API creds as env vars). Create/search/update.
- **Memories** — durable context; category, importance 1–5 (4–5 = always-include),
  when-to-use, tags; global or agent-scoped; create/search/update.
- **Rubrics / Evaluation** — Rubric Building, Rubric Search, Evaluation History,
  Improvement Backtesting.

## 8. Conversation & orchestration
- **Thread Search / Message Search / Thread Messages** — recall past work.
- **Follow-up Suggestions** — clickable next steps.
- **Agent Config / Execution History** — read config; list scheduled/webhook/
  email/live runs.
- **Agents & subagents** — spawn threads, delegate (subagent model), invoke named
  agents; invocation types: Thread, Slack, Telegram, Scheduled, Webhook/API,
  Email, Live Mode.

## 9. Integrations (third-party services, as tools)
- **Search / Connect / Execute Integration** — discover actions, connect
  (OAuth/API key), run actions.
- **Native (post-May-2026):** Google Workspace (Gmail, Calendar, Drive, Docs,
  Sheets, Slides, Contacts, Tasks), GitHub, Notion, Slack, Airtable, Databricks;
  plus Linear (per config docs). Salesforce/Snowflake appear illustratively.
- **Custom MCP servers** — connect any MCP-exposed service.
- **Skills with stored credentials** — call any API directly.
- Note: the "500+/1,000+ apps" figure is **Composio's** (legacy broker, disabled
  after the May 2026 incident), **not** a current Hyperagent claim.

---

Exposure strategy for all of the above → `tool-bridge.md`.
