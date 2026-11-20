# Clipnary Architecture Audit

**Date:** 2026-11-16  
**Repository:** local `C:\Users\DELL\Desktop\MY PROJECTS\Clipnary` worktree  
**Scope:** Code, README, AGENTS.md, dependencies, current local UI, and the existing test harness. Existing user changes were preserved; no feature implementation was started during this audit.

## Evidence labels

- **VERIFIED IN CODE** — read directly from the local repository.
- **VERIFIED IN BROWSER** — observed in the authenticated OpusClip tab, not inferred from code.
- **VERIFIED IN DOCUMENTATION** — confirmed by primary documentation or licence material.
- **PROPOSED** — recommended work.
- **UNVERIFIED** — not established by this audit.

## Executive assessment

Clipnary is not an empty prototype. It is a local-first FastAPI application with a usable end-to-end pipeline:

```text
Browser UI
   -> FastAPI security/session gate
   -> job creation and fair queue
   -> media probe/download or local upload
   -> YouTube captions when usable, otherwise local ASR
   -> transcript/loudness/chat signals
   -> AI candidate selection or loudness fallback
   -> FFmpeg/Pillow render
   -> local clip files + optional OAuth posting
```

**Honest rating:** current starter architecture **8/10 for a local MVP**, **5/10 for a reliable multi-user hosted service**, and **4/10 as an OpusClip-quality replacement** until highlight selection gains visual and emotional signals and the editor is hardened.

**VERIFIED IN CODE:** The repository declares an MIT licence. That applies to Clipnary's own code; it does not override the licences or usage terms of FFmpeg, model weights, fonts, platform APIs, downloaded media, or other bundled components.

## Repository map

| Component | Evidence | Responsibility |
|---|---|---|
| `studio/server.py` | VERIFIED IN CODE | FastAPI routes, local/shared-server gate, sessions, CSRF-ish same-origin checks, uploads, job APIs, OAuth callbacks, media serving. |
| `studio/config.py` | VERIFIED IN CODE | Environment settings, data/database paths, ASR/AI configuration, quotas and limits. |
| `studio/jobs.py` | VERIFIED IN CODE | Per-user fair queue, job lifecycle, cancellation, clip rendering queue, “find more”, manual cuts, remakes, resume/partial recovery. |
| `studio/media.py` | VERIFIED IN CODE | yt-dlp probing/downloads, YouTube captions, FFmpeg probing/audio extraction, ranged downloads, URL failure messages. |
| `studio/transcribe.py` and `studio/asr_worker.py` | VERIFIED IN CODE | Local/remote sherpa-onnx Parakeet word-timestamp transcription. |
| `studio/brain.py` | VERIFIED IN CODE | Timestamped transcript formatting, loudness z-scores, AI prompts/schema, candidate selection, boundary snapping, live judges, hook/title helpers. |
| `studio/render.py` | VERIFIED IN CODE | FFmpeg/Pillow layouts, ASS word captions, emoji overlay, audio filters, colour/zoom/fade/SFX effects, hardware encoder fallback. |
| `studio/live.py` | VERIFIED IN CODE | Rolling stream recording, chat activity, live transcript/reaction judges, trigger phrases, live clip queue. |
| `studio/accounts.py` and `studio/posting.py` | VERIFIED IN CODE | YouTube, Instagram, and TikTok OAuth/token handling, upload queue, scheduled posting, view/stat hooks. |
| `studio/db.py`, `auth.py`, `account.py`, `ctx.py` | VERIFIED IN CODE | SQLAlchemy database, optional sign-in, ownership context, session/security helpers. |
| `studio/storage.py` | VERIFIED IN CODE | Data-folder information, disk checks, folder movement, local cookie-file selection. |
| `web/index.html` | VERIFIED IN CODE | Single-file HTML/CSS/JS application UI; recipe modal, options, clip actions, activity/settings views. No frontend build step. |
| `tests/` | VERIFIED IN CODE | Permissions, abuse/limits, queue load, deletion, chunk uploads, AI service errors, local mode, Roman Urdu/Hindi captions, connected apps, limits, stuck clips, tools, storage. |

## Existing functionality to retain

### Input and media

**VERIFIED IN CODE:** Clipnary accepts YouTube/Twitch/Kick URLs and local uploads. It uses yt-dlp and FFmpeg, has metadata probing, thumbnail preview support, audio extraction, ranged download support, and explicit YouTube failure messages. YouTube browser cookies are opt-in through settings/local cookie file; the code does not attempt to bypass age verification or platform protection.

### Transcription

**VERIFIED IN CODE:** The default local speech path is sherpa-onnx with a Parakeet 0.6b model. It produces word timestamps, supports chunking, can use a remote ASR worker through `PEAKCUT_ASR_URL`, and falls back to local processing if the remote worker is unavailable. The README documents an approximately 480 MB first model download.

### Clip discovery

**VERIFIED IN CODE:** `brain.find_clips()` builds transcript lines, calculates loudness z-scores, splits long videos into 15-minute windows with 60-second overlap, asks the configured AI provider for timestamped candidates, snaps boundaries to transcript lines, removes overlaps, and caps the requested result count. If AI is unavailable, it uses a loudness-only fallback.

### Additive editing workflow

**VERIFIED IN CODE:**

- `request_cut()` adds a hand-selected clip without replacing existing clips.
- `request_more()` searches for clips not already used and appends them.
- `cancel_more()` stops the extra search while preserving existing clips.
- `request_render()` queues a remake with changed start/end, title/hook, style/layout, and effect flags.
- Job cancellation distinguishes queued/running/cancelling/cancelled states and marks pending work cancelled.

This directly addresses the user's requested behavior: old clips should stay while new clips are generated, and a running generation should be cancellable.

### Rendering and requested local effects

**VERIFIED IN CODE:** The current effect keys are `captions`, `emoji`, `speech_cleanup`, `audio_enhance`, `auto_sfx`, `color_correct`, `auto_zoom`, and `auto_transition`. The render path includes:

- ASS word-by-word captions and caption styles.
- Category-based emoji overlay.
- High-pass/low-pass/FFmpeg noise reduction for a basic speech cleanup mode.
- Dynamic-range compression plus loudness normalization.
- A short locally synthesized SFX tone; no external SFX API is required.
- Simple contrast/saturation/gamma correction.
- Gentle zoom via a larger crop.
- Fade in/out transitions.
- QSV encoder attempt with libx264 fallback.

These are useful free baselines. They are not equivalent to OpusClip's proprietary learned enhancement, visual layout, B-roll, dubbing, or face-aware correction systems.

### Live clipping and creator automation

**VERIFIED IN CODE:** Clipnary has rolling live recording, transcript and reaction-signal judges, chat activity input, trigger phrases such as “clip that”, creator workspaces, posting queues, scheduling, daily caps, and OAuth integrations for YouTube/Instagram/TikTok.

## Biggest current quality problem

The generic-clip problem is real. The normal long-video path gives the AI mostly a timestamped transcript plus loudness markers. It does **not** currently perform a full visual understanding pass, face/emotion tracking, laugh/applause classifier, speaker diarization/ranking, scene-change analysis, multimodal embedding retrieval, or a calibrated cross-modal reranker.

That creates predictable failure modes:

1. A well-spoken but unremarkable paragraph can score highly because the transcript sounds coherent.
2. A visually funny or gameplay-critical moment with little speech can be missed.
3. Steady loud music/background noise can create weak loudness candidates when the AI fallback is used.
4. A punchline can be clipped without enough setup, or setup can be included without the payoff.
5. Multiple windows can return semantically similar moments; overlap filtering is temporal, not semantic.
6. A model score is accepted as if it were calibrated probability. There is no local quality benchmark or creator feedback loop yet.

**VERIFIED IN CODE:** The live path is stronger than the normal path because it separately judges transcript words and reaction signals, and can incorporate chat. That design should be adapted to uploaded/recorded videos instead of rebuilding it from scratch.

## Architecture risks and limitations

### Processing and performance

- **VERIFIED IN CODE:** CPU ASR can be slow; a GPU/remote ASR worker is supported but optional.
- **VERIFIED IN CODE:** Rendering is synchronous within a background queue and has a long timeout; long clips, 1080p output, and multiple effects are expensive on CPU.
- **PROPOSED:** Add explicit stage timings, per-stage cancellation checks, and an estimate based on source duration, output resolution, encoder, and ASR mode.
- **PROPOSED:** Cache transcript, audio features, scene boundaries, and candidate windows so a remake does not repeat the expensive analysis.

### Persistence and concurrency

- **VERIFIED IN CODE:** Job state and clip metadata are stored in per-job JSON/files while account data uses SQLAlchemy/SQLite locally or PostgreSQL in a server deployment.
- **PROPOSED:** Keep JSON for local simplicity, but add atomic write/rename, schema versioning, file locks, and a recovery index before supporting many concurrent hosted users.
- **PROPOSED:** Move long-running jobs to a durable queue when hosted; in-process threads are acceptable for a single-user local MVP but not a resilient multi-instance service.

### Security and privacy

- **VERIFIED IN CODE:** Local mode defaults to loopback, account mode is optional, ownership checks/context are used, upload caps and disk checks exist, and source text is treated as untrusted before being sent to AI.
- **RISK:** OAuth refresh tokens, cookie files, and user media are sensitive. Never log them, place them in public media paths, or send them to an AI provider.
- **RISK:** If a shared-server mode is exposed to the Internet, add a real reverse proxy/TLS deployment, secret manager, rate limits, CSRF/session review, job isolation, and a documented threat model.

### YouTube and other source restrictions

- **VERIFIED IN CODE:** yt-dlp/browser-cookie support is opt-in and errors are surfaced when YouTube refuses access. It cannot guarantee age-restricted, bot-protected, private, or region-restricted downloads.
- **PROPOSED:** Treat local upload as the reliable path. For URLs, provide a clear diagnostic state and a user-controlled cookie file only when the user has rights and understands the privacy impact.
- **RISK:** “Can process every YouTube video” is a false product promise. Availability depends on visibility, rights, platform controls, extractor compatibility, and the user's own session.

## Current verification run

**VERIFIED IN CODE / LOCAL TEST RUN:** The system Python environment did not have SQLAlchemy, so `python tests/run.py` failed immediately with `ModuleNotFoundError`. Running the repository's `.venv` test command started the temporary test server and reported:

- permissions: 56 checks passed;
- abuse and limits: 40 checks passed;
- queue-under-load: did not finish within the 30-second verification window and was stopped, along with only its exact temporary test processes.

The existing local Clipnary server processes were left running. This means the full suite is **not certified by this audit**; the queue-load test needs a separate investigation. Earlier work in this worktree may have reported a full pass, but that result was not reproduced here and should not be treated as current evidence.

## Architecture conclusion

Clipnary's core should be extended, not replaced. The correct next technical investment is a cached, multi-signal highlight-ranking layer and a real editor model on top of the current job/render pipeline. Rebuilding the server, ASR, queue, or local effects first would spend time on components that already exist.

