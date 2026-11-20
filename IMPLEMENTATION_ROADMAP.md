# Clipnary Implementation Roadmap

**Date:** 2026-11-16  
**Goal:** Improve Clipnary toward a serious, local-first OpusClip-style product without making a paid third-party AI API a required dependency.

## Classification

- **A — Free/open-source on the user's hardware:** no recurring provider bill, but uses the user's CPU/GPU, storage, bandwidth, and electricity.
- **B — Free external API with quotas/restrictions:** may work at no API charge for limited use, but needs accounts, quotas, approvals, or policy compliance.
- **C — Paid external API/subscription:** must not be required for the roadmap.
- **D — Local but materially difficult/resource-heavy:** technically self-hostable, but needs serious engineering, GPU memory, model downloads, or licensing review.

## Technology and licence shortlist

The licence/API statements in the following table are **VERIFIED IN DOCUMENTATION**. The recommendations and class assignments are **PROPOSED**.

| Need | Recommendation | Class | Licence/evidence note |
|---|---|---:|---|
| Decode, crop, scale, audio filters, encode | Existing FFmpeg | A/D | FFmpeg's official legal page says the base is LGPL 2.1+ but optional parts/optimizations can be GPL. Decide which build/features are distributed and ship the applicable notices/source obligations. |
| URL acquisition | Existing yt-dlp | A | The official repository says yt-dlp is Unlicense but bundles components with separate licences. Site terms, rights, extractor availability, and account/session restrictions still apply. |
| Local ASR | Existing sherpa-onnx + Parakeet | A/D | sherpa-onnx source is Apache-2.0. Verify the specific downloaded model's terms separately before redistributing model files. |
| Local multimodal/text model | Optional Ollama adapter | A/D | Ollama's repository is MIT, but each model's weights/model card licence is separate. Do not equate a free runtime with unrestricted model redistribution or commercial use. |
| Scene-change candidates | PySceneDetect or FFmpeg scene filters | A | PySceneDetect's official repository is BSD-3-Clause. It is a detector, not a highlight-quality model. |
| Image/frame utilities | Existing Pillow | A | Current Pillow metadata identifies MIT-CMU licensing. Preserve notices and check bundled codecs/build dependencies. |
| Voice activity | Silero VAD candidate | A/D | The upstream project is commonly distributed under MIT, but pin a version and verify both code and model terms before packaging. |
| Audio features | Existing NumPy/soundfile plus optional librosa | A | Use for RMS/peak, spectral flux, silence, and speech/music features; no hosted AI call is required. |
| Local database/queue | Existing SQLite/SQLAlchemy/in-process queue | A | Suitable for local MVP. Use a durable worker/queue before multi-instance hosting. |
| YouTube upload | Existing OAuth/Data API integration | B | Google documents OAuth authorization and quota costs; uploads and writes are rate/quota limited and app setup is required. |
| Instagram Reels | Existing OAuth integration | B | Meta requires an eligible professional account and the relevant content-publishing permissions/API flow. |
| TikTok posting | Existing OAuth integration | B | TikTok documents `video.publish`, user authorization, app approval/audit, and restrictions for unaudited clients. |
| Hosted AI / hosted B-roll / hosted dubbing | Keep optional only | C | Never make this part of the required install. Put it behind an explicit BYO provider setting and a cost warning. |

**Important:** “Free” means free software, not zero cost. Local processing still consumes hardware time, disk, bandwidth, electricity, and sometimes a GPU.

## Verified progress — 2026-11-16

This milestone is implemented and verified locally:

- `studio/brain.py` now ranks candidates with deterministic transcript, reaction-word, audio-intensity-change, optional chat, user-preference, context-completeness, target-length, generic-content, and duplicate signals. AI scores are blended with these transparent signals instead of being accepted blindly.
- Natural-boundary snapping now avoids jumping across long transcript gaps and avoids manufacturing long clips when a nearby sentence boundary is unavailable. The default ranking target is approximately 18–35 seconds while explicit duration settings remain respected.
- AI-unavailable selection now uses the same deterministic multi-signal fallback instead of loudness alone. Selection telemetry reports candidate, ranked, accepted, fallback-window, duration, and target-length values.
- `studio/jobs.py` accepts and forwards the `moment_prompt` ranking hint, aggregates selection telemetry, and preserves the existing manual-cut, remake, Find More, and cancellation paths.
- The Windows queue-load test was fixed so multiprocessing spawn workers do not re-run the parent test at import time. No timeout was increased.
- `tests/test_highlights.py` adds deterministic coverage for exciting-vs-generic ranking, natural boundaries, duplicate prevention, loudness-only false positives, user preferences, fallback selection, telemetry, and existing-range exclusion.
- The complete local test suite passed after these changes. It uses deterministic fixtures rather than real sample videos, so real-world highlight quality is not yet verified.

Known limits for this milestone: the fallback lexicon is currently English-heavy, visual-only moments are not detected, and the existing UI does not yet expose the new `moment_prompt` option. Those are deliberate follow-up items; no UI redesign or heavy vision model was added here.

### Primary documentation used

- [FFmpeg licence and legal considerations](https://ffmpeg.org/legal.html)
- [yt-dlp licence](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE) and [yt-dlp dependency/licence notes](https://github.com/yt-dlp/yt-dlp)
- [sherpa-onnx licence](https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE)
- [Ollama licence](https://github.com/ollama/ollama/blob/master/LICENSE)
- [PySceneDetect licence](https://github.com/Breakthrough/PySceneDetect/blob/main/LICENSE)
- [YouTube Data API getting started and quota](https://developers.google.com/youtube/v3/getting-started)
- [YouTube video upload (`videos.insert`)](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
- [TikTok Content Posting API direct-post requirements](https://developers.tiktok.com/docs/en/content-posting-api-get-started)
- [TikTok direct-post reference and approval limits](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post)
- [Meta Instagram media/API requirements](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/v21.0/)

## Priority plan

### Phase 0 — Stabilise and measure before changing the picker

**Priority: P0.** No major UI redesign.

1. Add a fixture set of short, legally owned videos covering: talking head, gaming, podcast, reaction, music/background noise, quiet visual gag, multilingual speech, and live-chat-heavy content.
2. Save expected candidate windows and a small creator rating: `strong`, `usable`, `generic`, `wrong boundary`, `missed visual moment`.
3. Add a `pipeline_version` and `feature_schema_version` to every job/clip.
4. Record stage timings, transcript source, ASR mode, model name, token count where available, render encoder, and failure reason.
5. Fix the queue-load test before claiming the full test suite passes.

**Acceptance:** A repeatable local benchmark can compare ranking changes without relying on a paid API or a subjective demo only.

### Phase 1 — Upgrade highlight selection quality

**Priority: P0.** This is the core product differentiator.

Build a multi-stage pipeline that keeps the current `brain.find_clips()` contract but improves the evidence entering it:

1. **Candidate generation:** transcript sentence windows, pauses, volume spikes, laugh/applause likelihood, scene changes, chat spikes, and user-specified keywords.
2. **Context expansion:** add setup before the trigger and payoff after it; stop at sentence/scene boundaries instead of blindly padding.
3. **Feature extraction:** transcript embedding or local text-model relevance, speech density, silence/pause, loudness delta, spectral flux, VAD, scene-change proximity, face/presence signal where available, and chat rate.
4. **Reranking:** combine normalized signals with a transparent weighted score. Keep an evidence breakdown such as `story=0.8`, `reaction=0.6`, `visual_change=0.4`, `duplicate_penalty=0.2`.
5. **Quality gates:** reject sponsor/intros/dead air, incomplete sentences, excessive overlap, low speech confidence, and clips with no setup/payoff.
6. **Diversity:** use semantic similarity or transcript n-gram similarity to prevent twelve versions of the same moment.
7. **User prompt:** sanitize and apply “find moments about X” as a ranking boost/filter, not as an instruction that can override safety or output schema.
8. **Fallback:** if the AI/local model is unavailable, use deterministic multi-signal scoring rather than loudness alone.

**Why:** The present normal-video path is transcript-plus-loudness. That is why generic clips happen. A better prompt alone will not fix missed visual events or poor signal normalization.

### Phase 2 — Make the editor dependable

**Priority: P0.** Build on existing job APIs.

1. Add a source video player with a timeline, thumbnail strip, start/end handles, keyboard stepping, and visible duration.
2. Keep “Cut from original” additive; never replace generated clips.
3. Keep “Find more” as a separate run with an immutable `more_run_id`, old clips visible, and a cancel button.
4. Keep remakes versioned: `clip01_v1.mp4`, `clip01_v2.mp4`, with the previous successful version retained until the new render succeeds.
5. Make cancel state explicit: queued → cancelling → cancelled, with cleanup of only temporary work files. Do not delete old outputs.
6. Add a preview of captions/effects before expensive render where possible.

**Acceptance:** A user can change a range, click remake, cancel at any progress percentage, and still download the previous successful clip.

### Phase 3 — Expand local effects safely

**Priority: P1.** Deliver deterministic local features before model-heavy ones.

| Feature | First free implementation | Limitation |
|---|---|---|
| AI emojis | Category/keyword/reaction mapping + timed ASS overlay | Not true scene/emotion understanding. |
| Speech cleanup | VAD/transcript-aware pause/filler removal; FFmpeg denoise for background | Removing words requires re-timing captions and audio/video, not just a filter. |
| Enhance audio | Compressor, loudness normalization, optional denoise | Not a learned voice-isolation studio model. |
| Auto SFX | Short local synthesized accents + user-disable switch | No licensed SFX library; keep it subtle. |
| Auto color | Conservative exposure/contrast/saturation baseline | Not camera-aware grading. |
| Auto zoom | Gentle crop/scale; add face tracking later | Can crop the wrong person without face detection. |
| Auto transition | Fade/short cut rules around scene boundaries | Avoid transitions on every cut; they can reduce clarity. |
| Captions | Existing ASS styles, SRT import/export, safe font manifest | More styles increase QA/licensing burden. |

### Phase 4 — Add visual and emotional signals

**Priority: P1/P2, class D.** Add one signal at a time and measure it.

1. Scene-change detection for hard visual boundaries.
2. VAD and pause structure.
3. Laugh/applause/excitement audio classifier or a conservative feature detector.
4. Face/person presence and speaker/active-region tracking for crop/zoom.
5. Optional local vision-language model for a small set of sampled frames, only when a GPU or user-approved local model is available.
6. Semantic deduplication and diversity-aware top-k selection.

Do not start with a giant multimodal model. First make the deterministic candidate/reranker layer good enough that a model improves it rather than hiding its failures.

### Phase 5 — Transparent usage/cost accounting

**Priority: P1.** This is useful for the user's requested credit-like screen.

Store per job:

- source duration and processed range;
- requested clip count and actual clip count;
- ASR seconds and model name;
- local CPU/GPU wall time;
- render seconds, output resolution, and disk bytes;
- provider name, request count, input/output tokens when the provider supplies them;
- estimated BYO API cost with a clear “estimate” label;
- feature flags that caused extra work.

For local-only mode, show `No API cost` plus resource estimates. For BYO APIs, do not pretend all providers expose identical token prices, caching, or billing rules. Treat provider pricing as configuration with a timestamp and a source URL.

### Phase 6 — Publishing and creator automation

**Priority: P1/P2, class B.**

1. Keep local download as the reliable universal export.
2. Use OAuth, not raw user passwords or copied cookies, for YouTube/Instagram/TikTok posting.
3. Show the exact account, visibility, caption, and destination before posting.
4. Persist upload status and retry safely; never duplicate a post because a local request timed out.
5. Explain quota/approval constraints in Settings.
6. Keep platform integrations optional so the core clipper remains free and local.

## Dependency graph

```text
Source range + upload/URL
        |
        v
Metadata + audio + transcript cache
        |
        +--> audio/VAD/loudness/chat features
        +--> scene/frame features (optional)
        |
        v
Candidate windows --> context expansion --> reranker --> dedupe/diversity
                                                        |
                                                        v
                                        immutable clip records / more_run_id
                                                        |
                                                        v
                              editor/remake/versioned local render
                                                        |
                                                        v
                              download or optional OAuth posting
```

## Verified creation-workflow milestone — 2026-11-16

This follow-up milestone is now implemented and browser-checked:

- The creation recipe exposes source status/preview, start/end range controls, speech language, content genre, custom moment prompts, four prompt suggestions, a recommended 18–35 second target, custom duration bounds, and the existing caption/layout/effect controls.
- Language, genre, prompt, range, clip count, duration, and effects are collected by the existing jobOptions path and sent through the existing job API. Empty prompts remain automatic clipping.
- Generated clip cards and the clip editor show timestamps, duration, and available ranking evidence such as reaction, audio change, chat, prompt match, context, completeness, or generic penalty.
- The focused highlight and creation-option tests pass. The full local suite passes with 387 checks; the queue-load test passes without an increased timeout.
- Browser verification used the restarted local app at http://127.0.0.1:8766/app. Hindi and Reaction selection, a prompt suggestion, range 120–300 seconds, and the 18–35 second preset were exercised. Browser warning/error logs were empty.
- Real clip generation was not claimed: the YouTube source returned unavailable metadata and the Chrome upload bridge cannot set local files until its file-URL permission is enabled. Deterministic highlight fixtures remain the quality evidence.

The earlier note saying the UI did not expose moment_prompt is superseded by this section. Remaining limits are the English-heavy fallback lexicon, no visual-only moment detection, and provider cost display still being an estimate rather than billing reconciliation.

## Features that should remain optional

- Hosted AI APIs, paid B-roll, cloud GPU, managed storage, hosted transcription, and hosted dubbing are **C**, so they must not be required.
- Local vision-language models, face/eye-contact correction, high-quality voice dubbing, and learned audio restoration are **D**. Offer them as opt-in plugins with hardware/licence checks.
- Platform posting is **B**, not universally free: quotas, app approval, professional-account requirements, audits, and visibility restrictions apply.

## Technical and licensing risks

1. FFmpeg build/licence mode and codec patent exposure must be reviewed before distributing a commercial binary.
2. Model weights can have terms different from the runtime library. Record every model URL, version, checksum, and licence in a model manifest.
3. Fonts, caption templates, stock footage, emoji assets, SFX, and music need separate redistribution/use checks.
4. Downloading/reposting third-party video is a rights/platform issue; a rights checkbox is not legal permission.
5. Never ship a default shared API key. Users should supply their own key, or use local models.
6. Do not place browser cookies, OAuth tokens, uploaded media, or transcripts in logs or public URLs.

## What another coding agent should do next

1. Fix and isolate the queue-load test; record a reproducible baseline.
2. Add job/clip schema versions and timing telemetry without changing the UI.
3. Build the candidate-feature cache and evaluation fixtures.
4. Replace loudness-only fallback with deterministic multi-signal ranking.
5. Add transcript-aware user prompting and semantic/diversity deduplication.
6. Harden versioned remakes, additive “find more”, and cancellation cleanup.
7. Implement the timeline editor on top of those stable APIs.
8. Add scene/VAD features, then evaluate face/visual models only on hardware that can run them.
9. Add cost/resource estimates and provider pricing configuration.
10. Revisit social publishing, audit/approval, privacy, and licence compliance before public deployment.

## Final recommendation

The idea is viable and worth building: **8/10 as a local-first product direction**. You are wrong if you assume that adding every visible OpusClip toggle will automatically produce OpusClip-quality clips. The product's hard part is not the number of switches; it is selecting a genuinely memorable moment and keeping the edit stable, explainable, cancellable, and cheap to run locally. Build quality measurement and multi-signal ranking first, then expose the effects in the UI.

## Verified creation-studio milestone — 2026-11-17

Implemented and browser-verified in the existing FastAPI application:

- The homepage composer now keeps the first step focused on source selection and the primary `Make clips` action; the old visible Options button is removed.
- The creation workflow opens as a full-viewport studio with source status/preview, range controls, language, genre, custom moment guidance, prompt suggestions, clip count capped at 12, and a recommended 18–35 second duration target.
- Caption choices are presented as a 12-item renderer-backed gallery. Existing blur/zoom/crop layouts and four tested output ratios (9:16, 16:9, 1:1, 4:5) are selectable through the same backend job options.
- Enhancement controls are grouped in an expandable panel. Emoji presets, speech cleanup levels, zoom presets, color presets/sliders, and the supported edge fade transition are persisted and passed to rendering. Unsupported transition types are no longer advertised.
- Preset controls now enable their corresponding effect flags, and the renderer treats those flags as authoritative so a selected preset cannot silently change output while its effect is disabled.
- Focused creation tests cover option validation, output-ratio parity, caption gallery renderer compilation, and UI markers. The full local suite passed with 396 checks; the queue-load test passed without increasing its timeout.
- Browser verification used the running local application at `http://127.0.0.1:8766/app`. The new studio, prompt/range/language/genre/duration controls, gallery selection, aspect selection, enhancement preset interaction, and empty console warning/error state were observed. The provided YouTube URL reached the source lookup path but returned no usable metadata, so no real clip render is claimed here.

Remaining limits: the gallery is functional but still uses the existing ASS/FFmpeg renderer rather than a visual timeline editor; provider usage is an estimate, not billing reconciliation; and real-world clip quality still needs evaluation on local sample media. The next milestone should add a small authorized local-video fixture for end-to-end render verification, then measure output dimensions, cancellation, remake, and Find More behavior through the browser.

## Creation-studio visual alignment milestone — 2026-11-17

The existing creation workflow was visually aligned to the supplied dark media-editor reference without changing the dashboard or inventing unsupported actions:

- Added a dark, media-first studio surface with the Clipnary logo, source preview panel, adjust-range panel, visible range timeline, Recipe/Output context cards, and a fixed summary/sidebar.
- Moved the existing Create clips action into the summary area, kept Cancel beside it, and preserved the rights confirmation in the main workflow.
- Reorganized existing functional controls into readable cards and grouped enhancement rows with switch-style controls. Caption, layout, ratio, prompt, language, genre, duration, emoji, audio, color, zoom, and fade-transition behavior remain wired to the same backend options.
- Added accessible labels and state styling while keeping range text/selection indicators synchronized with the numeric and slider inputs.
- Browser verification confirmed the arranged studio, source lookup state, right-side Create action, dark surface, range update from 120–300 seconds, and zero console warnings/errors.

The supplied YouTube source still had unavailable metadata during this check, so the preview correctly showed a source-status placeholder rather than claiming a real thumbnail or generated clip. Auto-hook and brand-kit toggles remain intentionally absent as independent controls because the current backend has no separate tested switch for them; hooks are already produced as part of existing clip selection.

## Creation-studio source and live-preview milestone — 2026-11-17

The creation workflow now gives the user a usable source-first experience instead of opening the editor with unknown media:

- Link previews retry while checking and keep `Make clips` disabled until a usable source is ready. Failed lookups show a retry action and a specific recovery message; age-restricted YouTube videos are not bypassed.
- Source metadata now includes thumbnail, title, uploader, duration, description, and URL context. The range panel uses a visible two-handle timeline and stays synchronized with the numeric start/end fields.
- The right sidebar is now an output preview rather than billing/provider clutter. It updates for clip count, 18–35 second targets, portrait/square/landscape ratios, layouts, AI emoji cues, color, zoom, and supported transitions.
- Unsupported or inactive enhancement presets are disabled until their corresponding tested effect is enabled. Emoji behavior/frequency controls were removed from the visible workflow as requested; the existing emoji feature remains a single functional switch.
- Browser verification used the running local app at `http://127.0.0.1:8766/app`: public Big Buck Bunny metadata and thumbnail loaded, prompt/language/genre/duration changes were reflected, the range changed to 2:00–4:00, a 4:5 zoomed preview with AI emoji/color/zoom/transition state was visible, and browser warning/error logs were empty. The supplied age-restricted URL showed the checking state followed by the recovery message and a disabled retry-state action.
- The custom regression runner passed **398 checks**, including the queue-load section without increasing its timeout. `git diff --check` and the embedded web-script syntax check also passed.

No real clip render is claimed in this UI milestone. The next milestone should use an authorized local video fixture to verify generated output dimensions, cancellation, remake, and Find More behavior end to end.

## Shorts layout and caption-picker milestone — 2026-11-17

- The creation workflow is now Shorts-first: the visible output-ratio control exposes only the selected `9:16 Shorts` target. Other backend aspect values remain accepted for API compatibility, but are no longer presented in this workflow.
- The range strip now renders a real filmstrip-style row of source-thumbnail frames with a highlighted selection boundary, while numeric start/end fields remain available as the non-drag alternative.
- Blur and zoom geometry now use distinct, larger foreground scales for vertical output; crop remains a full-frame center crop. This is an aspect-aware deterministic improvement, not face tracking, so off-center subjects may still need a future smart-crop step.
- Layout cards use the selected source poster instead of generic gradients, and the live preview updates when Blur, Zoomed In, or Full Screen Crop is selected.
- Caption selection now includes 28 renderer-backed presets, including Word Cut-like clean styles, Marker Sweep, Karaoke, Punch, Retro 3D, Highlighter Box, Sticker, Comic, and Handwritten-inspired variants. They reuse bundled fonts and ASS/FFmpeg rendering; no paid font/API dependency was added.
- Focused tests pass: creation options, geometry distinctions, portrait-source fallback, all caption presets compiling to ASS, web-script syntax, and `git diff --check`. The full regression run also completed with all checks passing.
- Browser verification on `http://127.0.0.1:8766/app` confirmed source metadata, the filmstrip, 9:16-only output, source-backed layout cards, Zoomed In live preview, expanded caption choices, and zero browser warning/error logs.

Remaining limitation: layout selection is now materially better, but it still uses center-based crop because automatic face/subject tracking is not implemented. Validate the three layouts with an authorized local video before treating visual quality as production-ready.

## Shorts-only layout and enhancement controls milestone — 2026-11-17

- Removed the visible Output ratio section and ratio cards from the creation workflow. The internal aspect remains fixed to vertical for Shorts and is preserved in the API payload for compatibility.
- Renamed the three visible layout choices to Full Length, Zoomed, and Box, while keeping the existing renderer keys (crop, zoom, and blur) stable. The right preview badge and summary stat now follow the selected layout only.
- Added a functional transition gallery for None, Fade, Dip to black, and White flash. These are edge treatments on each generated clip; the app does not yet concatenate multiple clips into one timeline, so these are not cross-clip transitions.
- Reorganized enhancement controls into a transition panel and a Picture adjustments panel with live values for brightness, contrast, saturation, and newly renderer-backed sharpness.
- Renamed the language control to Caption language, removed the visible Content genre control and Other language option, and expanded the supported language list. The existing backend field remains speech_language because it is currently the tested transcript-language hint; caption translation remains limited by the existing renderer/AI behavior.
- The live preview now applies the selected caption style's font/color treatment instead of always showing the same generic caption appearance. The usage-rights confirmation is now a dedicated aligned card.
- Focused creation tests and the full regression suite passed. Browser verification on http://127.0.0.1:8766/app confirmed that Output ratio and Content genre are absent, the three layout cards are visible, caption language selection works, caption/layout/transition selections update the right preview, picture sliders update live values, and browser console warnings/errors are empty.

Remaining limitations: the layout renderer is still center-based rather than face-aware; transition choices apply to clip edges rather than between a combined sequence; and a selected Caption language currently acts as the existing transcript-language hint rather than a general target-language translation control.

## Caption language, Shorts geometry, and live adjustment milestone — 2026-11-17

- Added a separate `caption_language` option while preserving `speech_language` for backwards-compatible source/transcript hints. Explicit Urdu, Hindi, and other supported target languages now stay in the requested display language; a failed translation keeps the timed source words instead of silently inventing English output.
- The renderer no longer applies unconditional Romanisation after caption selection. Existing legacy `english_captions` behavior and its tests remain intact, while the new target-language path is covered by mocked AI/fallback tests.
- Reworked the range overview to a source-independent waveform-style strip. It no longer paints the video thumbnail behind the range controls; the two numeric fields and two-handle range control remain the authoritative selection inputs. The current bars are a deterministic audio overview, not sampled amplitude analysis.
- Corrected the visible Shorts layout semantics: Full Length fills the 9:16 frame, Zoomed keeps the existing closer crop, and Box uses the softened canvas plus a centered framed source. Box renders now include a subtle orange frame so preview and FFmpeg output agree more closely.
- Caption-off now removes the caption layer from the live preview entirely. Caption template selection continues to change the preview typography/treatment. Transition cards include restrained hover demonstrations with reduced-motion fallback; current transitions remain per-clip edge treatments, not concatenated clip-to-clip transitions.
- Picture sliders are always movable. Changing brightness, contrast, saturation, or sharpness enables the renderer-backed color correction path and updates the live values/preview immediately. The old disabled-slider state was a genuine interaction bug.
- Removed the visible No creator selector from the home composer as requested.
- Verification: focused creation and caption tests passed; the full regression runner passed all checks; embedded JavaScript syntax and `git diff --check` passed; an FFmpeg fixture rendered 12 clips across all three layouts at 1080x1920 with approximately 2.8s requested durations; browser verification on `http://127.0.0.1:8766/app` showed source metadata, waveform range, Urdu selection, 12 clips, 25–35s, layout switching, caption-off removal, live sliders, and zero warning/error logs.

Remaining limitations: the waveform is visual guidance rather than decoded amplitude data; target-language translation still requires the configured AI when source and target differ; the renderer remains center-based rather than face-aware; and no real YouTube render was claimed because age-restricted/provider downloads are not bypassed. The next milestone should add an authorized speech-bearing local fixture and verify actual transcription, target-language burn-in, cancellation, remake, and Find More through the browser.

## Navigation, platform workspace, and clip-editor access milestone — 2026-11-17

Verified progress in the existing application:

- Replaced the visible left-sidebar navigation with a responsive branded top navigation. It now exposes Home, All videos, Creators, Connected platforms, Post queue, and Settings without removing the existing creator workspaces or live-recording setup.
- Added a real Creators dropdown with Add new creator, workspace links, and per-creator delete actions guarded by the existing confirmation flow. The delete action uses the existing `DELETE /api/creators/{id}` endpoint and keeps the existing creator/media ownership behavior.
- Added `/app/platforms` as a first-class route backed by the existing Connected apps/OAuth implementation. It shows YouTube, Instagram, and TikTok setup state, real connect/disconnect controls, the generated callback URL with copy support, and official documentation links.
- Added `/app/queue` backed by the existing overview/posting API. It shows scheduled, posting, posted, and failed items and reuses the existing pause/cancel/retry actions.
- Improved clip cards with an explicit Edit action. The existing editor now exposes renderer-backed trim boundaries, caption/layout selection, enhancement toggles, transition selection, brightness/contrast/saturation/sharpness sliders, Reset picture, Preview, Export, and Save and re-make.
- Re-rendering is still non-destructive at the UI level: when a finished clip is re-made, the previous rendered cover/video remains visible with a “Rendering new version” state until the new render succeeds. Existing clips are not removed by Find more or a remake.
- Added `tests/test_navigation.py` for navigation, OAuth route, bulk-delete, and editor wiring contracts; included it in `tests/run.py`.

Validation:

- `tests/run.py`: all suites passed.
- `tests/test_navigation.py`: 22 checks passed.
- `tests/test_creation_options.py`: 40 checks passed.
- Inline JavaScript syntax check and `git diff --check`: passed.
- Browser smoke verification on `http://127.0.0.1:8766/app`: top navigation, Creators dropdown, `/app/platforms`, callback URL/copy panel, `/app/queue`, and their visible state were verified. No console errors were observed during this smoke check.

Limitations still open:

- The current local account had no finished clip, so the new editor toolbar and re-rendering visual state were verified by code contracts but not opened against a real generated clip in the browser during this milestone.
- The renderer currently supports the existing three Shorts layouts (Full Length/crop, Zoomed, Box/blur), not arbitrary split-screen, facecam, speaker-focus, or free-form caption positioning. Those should not be exposed until renderer support is implemented and tested.

## Home, API connection, and creator-video navigation milestone — 2026-11-17

- Removed the visible Settings entry from the top navigation and account menu. The existing settings routes and backend endpoints remain for compatibility, but normal users now reach provider/platform setup through Platforms and the API connection labels.
- Simplified Home to the useful dashboard surface: active recordings, clips today, posts today, Gemini API calls today, the activity graph, and the Gemini API usage card. The old Next steps, Creators summary, and Post queue cards no longer repeat navigation or confuse the home view.
- Renamed the visible AI setup tab to API connection and Connected apps to How to connect. The platform page now explains OAuth setup and keeps the real YouTube/Instagram/TikTok setup cards, callback copy action, and official documentation links.
- Removed the confusing browser-profile, cookies.txt, and YouTube link-access controls from the visible platform page. The local troubleshooting endpoints remain intact for existing installations; the UI now explains that age-restricted links are not guaranteed and uploading the source file is the reliable path.
- Stabilized the Creators dropdown across refreshes and added creator-workspace source actions: public source titles/thumbnails open on YouTube, Copy link works, Use link sends a URL back into the clipping composer, and Delete local is offered only for a locally imported Clipnary job.
- Added `GET /api/creators/{cid}/recent-videos`, using yt-dlp flat extraction for public YouTube channel metadata only. It filters to the last 30 days, caches lookups briefly, never downloads media, and reports unsupported/non-public channel failures instead of fabricating entries.

Validation:

- Full `tests/run.py`: all suites passed, including queue-load, highlight-selection, creation options, and the new navigation/recent-video contracts.
- `tests/test_navigation.py`: 29 checks passed. Python compilation, inline JavaScript syntax, and `git diff --check` passed.
- Browser verification on `http://127.0.0.1:8766/app`: Home showed the new metrics and Gemini API card; Settings was absent from top navigation; Creators opened with Add new creator, workspace, and delete controls; Platforms showed API connection/How to connect and no browser-cookie controls; browser console warnings/errors were empty.

Remaining limitations:

- The existing IShowSpeed workspace has no saved YouTube channel URL, so the browser could verify the empty-state path but not a real last-month video grid. A real public channel URL or authorized test creator is still needed to validate remote thumbnails and the recent-video response end to end.
- “Delete” cannot remove a video from YouTube; it only removes a locally imported Clipnary job. The current three posting platforms and OAuth approval requirements remain unchanged.

## Creator dropdown, onboarding links, and navigation cleanup milestone — 2026-11-17

- Replaced the non-interactive visible Creators summary with an explicit accessible button and menu. The menu exposes Add creator, saved creator workspaces, and the existing guarded delete action; selecting a workspace still opens its creator page.
- Reworked Add creator into a real modal form with Name and Channel link fields, channel metadata preview loading, native validation, and a visible Saving creator spinner while the existing `POST /api/creators` request completes. No creator data was created during verification.
- Added a loading skeleton with `aria-busy` to the creator’s last-30-days YouTube video list. The existing backend still uses flat public metadata extraction, returns thumbnails/links, and keeps Use link, Copy link, and Delete local actions.
- Added direct official setup links for Google Cloud/YouTube, Meta/Instagram, and TikTok Developer inside “Which setup do I need?” so users can reach the correct developer console from the app.
- Removed Post queue from the visible top navigation and removed the GitHub/Instagram promotional header actions. The queue route and posting actions remain in the backend and existing clip flow for compatibility; they are no longer presented as primary navigation.

Validation:

- `tests/test_navigation.py`: all 36 checks passed after adding the Creators trigger, save-state, loading skeleton, and official setup-link contracts.
- Full `tests/run.py`: all suites passed, including queue-load, highlight selection, creation options, deletion/bulk actions, captions, storage, and navigation.
- Inline frontend JavaScript syntax, Python compilation, and `git diff --check` passed.
- Browser verification on `http://127.0.0.1:8766/app` confirmed the clickable Creators menu, Add creator modal, All videos route, Platforms setup tutorial links, removal of Post queue and promotional header buttons, and no browser console warnings/errors. The existing IShowSpeed workspace has no saved channel URL, so a populated remote 31-day thumbnail grid was not claimed.

Remaining limitations:

- Saving a creator and fetching a real creator’s YouTube uploads were not submitted in the browser during this verification to avoid changing the user’s local data or relying on a third-party channel. The request paths and loading/error states are implemented; a real public channel should be used for the next end-to-end check.
- Post queue is hidden from primary navigation but not deleted from the backend or clip-post dialog, preserving existing posting compatibility.

## Creator workspace routing and API usage reset milestone — 2026-11-17

- Creator dropdown workspace links now explicitly open the Clips tab, so clicking a creator cannot leave the user on the previous Setup or Activity tab.
- A creator without a saved YouTube channel now receives an actionable empty state with an Open creator setup button instead of a blank workspace. New creators require a channel URL, while Twitch/Kick connection fields remain available for live-recording setup.
- The creator recent-video panel retains its loading skeleton and public YouTube metadata path for the last 30 days. It shows thumbnails, titles, dates, durations, source links, Use link, Copy link, and local delete actions when metadata is available.
- Added a guarded `POST /api/usage/reset` action. It deletes only the signed-in user’s AI usage rows and refreshes the usage totals/graph; API keys, creators, source videos, generated clips, and posting data are untouched.
- Added the Reset usage control to the API usage page with an explicit destructive confirmation dialog and accessible label/state.

Validation:

- Full `.venv\Scripts\python.exe tests\run.py`: all suites passed, including queue-load, highlight-selection, creation options, navigation, deletion, captions, AI services, and storage.
- Focused navigation and AI usage tests passed, including per-user usage-reset isolation. Inline JavaScript syntax, Python compilation, and `git diff --check` passed.
- Browser verification on `http://127.0.0.1:8766/app`: creator dropdown routing opened the Clips workspace; the missing-channel setup CTA was visible; API usage showed Reset usage and its guarded confirmation; browser console warnings/errors were empty.

Remaining limitations:

- The existing IShowSpeed record still has no saved YouTube channel URL, so the browser check intentionally verified the setup CTA rather than claiming a populated remote 30-day grid. Save a real public channel URL to exercise that path.
- Usage reset was opened and cancelled during verification so existing local usage data was not destroyed. The backend reset path is covered by tests and the UI confirmation is wired.

## Dedicated creator management page milestone — 2026-11-17

- Changed the main Creators navigation label into a real link to `/app/creators`; the separate plus control remains available for the quick dropdown.
- Added a dedicated creator-management page with a left-side creator directory, saved creator count, `+ Add creator`, per-creator Delete actions, and a selected creator information panel.
- Selecting a creator from the directory opens the existing creator workspace. The workspace keeps the public last-30-days YouTube feed with thumbnails, durations, upload date and local time, an explicit Open YouTube action, Copy link, and Use link for clipping.
- Kept the existing guarded delete flow so deleting a creator requires confirmation and removes its local settings/media only after explicit confirmation.
- Reworked recent-upload timestamps to use YouTube's public RSS feed alongside fast flat playlist extraction. The creator page no longer performs a serial full-metadata lookup; it shows exact published date/time when the public feed provides it and keeps the loading path bounded.

Validation:

- Full `.venv\Scripts\python.exe tests\run.py`: all suites passed; navigation/clip-editor checks reached 45 before the final timestamp contract, and the focused navigation suite now passes 46 checks.
- Browser verification: Home → Creators opened `http://127.0.0.1:8766/app/creators`; the page showed the left creator list and Add/Delete controls. A second public test creator was saved and its workspace opened with the recent YouTube feed and expected actions. Browser console warnings/errors were empty.
- Browser verification after the timestamp fix: the first creator video card showed `Uploaded Nov 14, 2026, 10:00 PM`, `Open YouTube`, `Use link`, and `Copy link`; the local recent-video request completed in about 3.6 seconds for the test channel.
- Frontend JavaScript syntax and `git diff --check` passed.

Remaining limitations:

- The test creator added during verification is a real local creator record; remove it from the Creators page if it is not wanted. No creator or clip is deleted automatically.
- YouTube’s public metadata availability can change or fail for private/age-restricted channels; the local upload path remains the reliable fallback.

## Creator recent-video URL and refresh fix — 2026-11-17

- Fixed recent-upload discovery for creator URLs saved without a scheme, such as `www.youtube.com/@IShowSpeed`. Profile lookup already accepted those URLs, but the recent-video path passed the bare value to yt-dlp and could silently return an empty playlist.
- Wired the existing Refresh action to the backend cache: `?refresh=1` now forces a fresh public metadata lookup instead of returning the previous empty result.
- Made the creator workspace source-aware for YouTube, Twitch, and Kick. A creator without a saved source now receives a generic setup message, and non-YouTube sources are no longer mislabeled as missing YouTube channels. Twitch/Kick recent-upload listing still reports its actual support limitation rather than inventing videos.

Validation:

- Focused `tests/test_navigation.py`: all 48 checks passed, including bare-URL normalization and refresh-cache contracts.
- Direct smoke test against `www.youtube.com/@IShowSpeed` with the local backend: 5 public videos returned inside the 30-day window, with titles, thumbnails, timestamps and durations where available.
- Browser verification on `http://127.0.0.1:8766/app/creators/ishowspeed`: the page displayed `Last 30 days · 5 found` and the five video cards with thumbnails, dates, Open YouTube, Use link and Copy link actions. No browser console errors were observed.
- Python compilation and `git diff --check` passed.

Remaining limitations:

- The complete `tests/run.py` was not clean in this already-used local data directory: permissions/abuse tests reused existing email records, and the big-upload test could not connect to its expected test server port. The relevant focused suite and the live 8766 endpoint passed; these failures are test-environment isolation issues, not evidence that the creator fix failed.
- Recent public uploads remain dependent on each platform’s public metadata. YouTube is now working for the saved creator path; Twitch/Kick VOD listing is still a separate follow-up.

## Creator workspace header and thumbnail layout fix — 2026-11-18

- Replaced the creator workspace header’s absolute-centered Clips/Setup/Activity tabs with a normal desktop flex-row placement. The tabs now align with the global navigation and no longer overlap Creators or Platforms as the header content grows.
- Changed recent-video thumbnails to a fixed 168×94 preview box with `object-fit: contain`, preserving the complete source image for portrait, 4:3, and other non-standard thumbnails instead of cropping them with `cover`.

Validation:

- `tests/test_navigation.py`: all 52 checks passed, including header-row and complete-thumbnail contracts.
- Browser verification on `http://127.0.0.1:8766/app/creators/ishowspeed`: header tabs computed as `position: static` with no transform; thumbnail previews computed as 168×94 with `object-fit: contain`; all five thumbnail images reported loaded with 480×360 source dimensions.
- Python compilation and `git diff --check` passed.

## Responsive creator feed, live/VOD discovery, and API-key removal — 2026-11-18

- Expanded YouTube creator discovery to merge public `/videos`, `/streams`, and `/shorts` playlists, deduplicate entries, apply the 30-day timestamp window, and exclude future scheduled events. Live-stream VODs and Shorts now appear alongside normal uploads when public metadata exposes them.
- Added responsive creator-feed rules: two-column cards at tablet widths, one-column cards on phones, full-width contained thumbnails on narrow cards, and a full-width creator tab strip below the compact header so global navigation, creator identity, and tabs do not compete for one row.
- Added a guarded `Remove API key` action to API connection settings. The action requires confirmation, clears only the saved dashboard key, leaves creators/videos/clips untouched, and returns the app to deterministic fallback clipping until another key is saved.
- Added a visible `API connection` shortcut beside `Reset usage` on the API Usage page, so the provider/key controls are reachable without guessing a hidden settings URL.

Validation:

- Live API smoke test for IShowSpeed returned 15 public entries in the last 30 days, including regular uploads, stream/VOD entries and Shorts; visible dates ranged from Nov 6–17, 2026 and the current Nov 18 date makes those timestamps valid.
- Browser verification on `http://127.0.0.1:8766/app/creators/ishowspeed`: `Last 30 days · 15 found` rendered with thumbnails, dates, durations and actions; API connection visibly showed `Remove API key`; API Usage visibly showed the API connection shortcut; browser console warnings/errors were 0.
- Focused suites passed: queue-load, highlight selection, creation options, Hindi/Urdu caption handling, local API flow (including remove/reconnect), and navigation contracts. Python compilation and `git diff --check` passed.

Remaining limitations:

- The current IShowSpeed profile was offline during verification, so the live player correctly stayed hidden. The existing live path is wired to refreshed platform profile state and will show the live panel/player when a supported channel is actually live; a live session was not fabricated for testing.
- YouTube’s public RSS feed exposes a bounded recent set, so the app can show fewer than every upload if a channel publishes more than the feed window in 30 days. Complete historical coverage requires an authorized YouTube Data API configuration; the UI reports the public entries it actually discovered rather than claiming missing videos.
- Twitch/Kick recent VOD listing remains a separate follow-up; those sources are currently identified honestly as unsupported for the 30-day feed.

## Clipnary shell/theme milestone — 2026-11-18

- Replaced the visible Clipnary character/logo treatment with a text-based Clipnary wordmark and a small C/play SVG mark. The old character asset is no longer used by the app shell or clip-creation header.
- Removed Home, All videos, Creators, and Platforms from the visible global top navigation. Existing routes and in-product actions remain intact; the header now focuses on the centered page/workspace identity and creator tabs.
- Applied the Clipnary-inspired dark navy/slate theme with lime accent styling, dark dropdown/panel surfaces, improved contrast, and responsive header behavior.
- Corrected dark `brand-ink` text leaking into the dark shell: hero headings, page title, activity headings, metrics, and dashboard values now render with the light text token while lime action buttons keep intentional contrast.
- Added a right-side Instagram slot as a safe disabled placeholder until the owner supplies the exact Instagram URL. No invented or guessed social link was added.
- Kept the repository private and made no GitHub publishing or visibility changes.

Validation:

- `tests/test_navigation.py`: all checks passed after updating the contract for the intentionally removed global nav links.
- `tests/test_creation_options.py`: all checks passed; existing creation controls and recipe-backed behavior remain present.
- Browser verification on `http://127.0.0.1:8766/app`: the running page loaded as `Clipnary — AI clip studio`, showed the dark shell, centered page identity, Clipnary wordmark, and Instagram placeholder. The old global destination links were absent from the rendered header.
- Browser contrast verification: computed colors for the hero heading, page title, and dashboard metric were all `rgb(247, 249, 255)` (the light text token).
- `git diff --check` passed.

Remaining limitations:

- The actual Instagram URL is still required before the placeholder can become a clickable external link.
- This milestone changes the shell/theme only; it does not redesign the clip editor or replace existing backend behavior.

## Navigation and range-timeline correction — 2026-11-18

- Restored the visible Home, All videos, Creators, creator dropdown, and Platforms navigation links. The previous shell pass hid them too aggressively; the existing pages and routes remain part of the product and should stay discoverable.
- Kept the Clipnary visual treatment without replacing the existing page content or navigation behavior.
- Replaced the range-strip thumbnail placeholder with a deterministic audio waveform timeline using violet/lime bars. Start/end range handles and duration labels remain connected to the existing controls.

Validation:

- Browser verification: Home, All videos, Creators, and Platforms opened at their existing routes from the restored themed header.
- Focused creation contract now checks for `range-waveform` and rejects the old placeholder thumbnail markup.

## Clipnary branding and centered page-title cleanup — 2026-11-18

- Replaced user-facing legacy logo references in the app shell, auth/reset/admin/legal/landing pages, empty states, and studio header with the new Clipnary mark/wordmark assets. Legacy files remain on disk for compatibility, but are no longer referenced by the rendered product.
- Kept the existing Home, All videos, Creators, creator dropdown, and Platforms destinations visible after the earlier theme pass hid them too aggressively.
- Kept the current page name in the centered header cluster and hid only the repeated greeting/subtitle text, so each page still has a clear centered identity without duplicating copy on every screen.
- Kept Instagram as a disabled placeholder until the owner provides the real URL; no guessed external link was added.

Validation:

- Browser verification on `http://127.0.0.1:8766/app`: `Home` is visible as the centered page heading, the repeated `Good morning...` subtitle is not displayed, and the global navigation exposes Home, All videos, Creators, and Platforms.
- `tests/test_navigation.py`: all checks passed.
- `tests/test_creation_options.py`: all checks passed, including waveform timeline and hidden output-ratio picker contracts.
- `git diff --check` passed.

Remaining limitations:

- The exact Instagram URL is still required before the placeholder can become a clickable social link.
- This cleanup does not delete legacy asset files or rename every historical Clipnary string in email/legal copy; it removes the old logo from the visible application surfaces without risking unrelated compatibility.

## New-user dashboard and API setup states — 2026-11-18

- Replaced the fresh-dashboard wall of zero-valued metric cards with a real `No activity yet` state. Metrics return when there is actual recording, clipping, publishing, view, or earnings activity.
- Replaced the dashboard’s provider/model card for an unconfigured account with `Select your AI model`, an explicit API-connection CTA, and a still-available usage link. No model name is shown while the API is not ready.
- Added a model-gated API Usage empty state. It keeps the records page intentionally empty until a provider, key, and model are configured; previously recorded usage remains visible if a configured model is later removed.
- Renamed dashboard labels to product-specific terms such as `Live sessions`, `Clips created today`, `Published today`, and provider-specific `AI runs today` rather than hard-coding Gemini into the empty dashboard.
- Restyled the upload control to use the dark Clipnary surface tokens and replaced the Creators plus glyph with a caret while preserving the creator workspace menu and Add creator action.
- Connected the Instagram header action to the owner's handle `https://www.instagram.com/bildup.co/`.

Validation:

- Browser verification on the running configured app at `http://127.0.0.1:8766/app`: Instagram href, dark upload control, caret menu, centered title, and hidden repeated subtitle were observed.
- Browser verification on an isolated fresh-data instance at `http://127.0.0.1:8767/app`: no metric tiles, `No activity yet`, blank model display, `Select your AI model`, and both `Choose model` / `View API usage` actions were observed.
- Isolated fresh-data API Usage route: `Select your AI model` rendered with no usage tiles or reset action until configuration exists.
- `tests/test_navigation.py`: all checks passed, including new empty-state, upload-theme, caret, and Instagram-link contracts.
- `tests/test_creation_options.py`: all checks passed.
- Python compilation and `git diff --check` passed.

Remaining limitations:

- The existing saved AI configuration was not reset; the fresh-user behavior was verified in an isolated data directory so existing keys, creators, videos, and clips were preserved.
- The Instagram handle is mapped to `https://www.instagram.com/bildup.co/`.

## Centered navigation and How to use page — 2026-11-18

- Added a routed `How to use` page before Home in the global navigation. It explains the existing source, selection, generation, and review workflow and links to the interactive tour and clipping flow.
- Removed the separate Creators caret/dropdown from the global header. Creators remains a normal destination, while creator workspaces and Add creator stay available on the Creators page/sidebar.
- Centered the global navigation between the Clipnary mark and the right-side Instagram action on desktop, with a responsive full-width navigation row on smaller screens. Creator identity/tabs move to a separate row on creator workspaces to avoid overlap.
- Mapped the Instagram value to `https://www.instagram.com/bildup.co/`.

Validation:

- Focused navigation contract updated for the new route, plain Creators destination, and responsive centered layout.
- Browser verification on `http://127.0.0.1:8766/app`: confirmed the five-item order, no Creators dropdown, centered navigation, and the Instagram action at the right edge. Clicking `How to use` opened `/app/how-to-use` with the four workflow steps and both working CTA buttons.

## Uiverse-inspired interaction and platform branding pass — 2026-11-18

- Removed the Interactive Tour entry point from the How to use page and account menu. The old automatic first-login tour no longer launches; the walkthrough video can be added once the owner supplies the actual video file.
- Added local YouTube, Instagram, and TikTok brand-mark SVGs for the platform connection cards. The marks are based on the official brand resources, rather than generic placeholder glyphs or runtime-hosted images.
- Added a restrained interaction layer inspired by the reference library: color/border hover states for buttons and cards, focus-within feedback for connection cards, staggered How to use page entry animation, and reduced-motion handling. No drop shadows or backend behavior were introduced.

Reference checks:

- Uiverse describes its library as open-source UI elements with button hover effects, loaders, cards, and animated controls; Clipnary uses the interaction principles only and does not copy a specific component.
- Official brand resources checked: [YouTube Brand Resources](https://brand.youtube/), [Instagram Brand Resources](https://www.meta.com/brand/resources/instagram/instagram-brand/), and [TikTok brand resources](https://www.tiktok.com/about/brand-resources).

Validation:

- Browser verification on `http://127.0.0.1:8766/app/how-to-use`: the page rendered four steps and `Start clipping`; no Interactive Tour control was present.
- Browser verification on `http://127.0.0.1:8766/app/platforms`: YouTube, Instagram, and TikTok cards loaded the three local SVG marks successfully at 25×25px.
- `tests/test_navigation.py`, `tests/test_creation_options.py`, JavaScript syntax, SVG presence checks, and `git diff --check` passed.

## API provider picker and creator dialog polish — 2026-11-18

- Replaced the generic native API-provider select with a Clipnary-styled custom picker in the API connection page. Each provider now has a compact badge, a useful one-line description, selected-state checkmark, hover/focus treatment, and Escape/outside-click closing behavior.
- Kept the native `#ai_provider` select hidden as a compatibility field so existing model discovery, save/test, remove-key, and provider-change logic still receives the selected provider.
- Fixed regular dialogs that sit outside `.app` so the New creator dialog uses the dark Clipnary surface, readable theme text, dark inputs, and visible secondary actions instead of falling back to the old light dialog palette.

Validation:

- Browser verification on `http://127.0.0.1:8766/app/settings/ai`: picker opened with 8 provider options and descriptions; selecting OpenAI changed the compatibility field to `openai` and closed the menu.
- Browser verification on `http://127.0.0.1:8766/app/creators`: the visible Add creator action opened the New creator dialog with the dark surface, themed border, readable help text, and dark input field.
- `tests/test_navigation.py`, `tests/test_creation_options.py`, `tests/test_ai.py`, `tests/test_local.py`, and `tests/test_load_queue.py <repo-root>` passed; JavaScript syntax and `git diff --check` passed.

## Local icon interaction and provider marks — 2026-11-18

- Added `data-icon` metadata to the existing local SVG helper so navigation, workflow, setup, creation, review, and API actions share one hover/focus interaction contract.
- Added a restrained Lordicon-inspired colour animation for interactive marks. It changes colour only, follows the existing no-shadow visual rule, and is disabled by the existing reduced-motion media rule.
- Added local vector marks for Gemini, OpenAI, xAI/Grok, Groq, OpenRouter, Claude/Anthropic, and Ollama in the API provider picker. Custom retains a readable API fallback because it has no provider brand.
- Added meaningful marks to the API save, test, and remove-key actions.
- Added colour-based hover feedback to platform brand images without changing their silhouettes or requiring a remote icon runtime.
- Replaced the generic plus mark on the `Connect API` banner CTA with the existing API connection plug mark, and applied the same mark to API connection shortcuts.

Validation:

- Browser JavaScript parse: passed.
- `tests/test_navigation.py`: passed, including the local icon hover contract, provider vector fallback contract, and API action icon contract.
- `tests/test_creation_options.py` and `tests/test_ai.py`: passed.
- Running app verification on `http://127.0.0.1:8766/app/settings/ai`: eight provider options rendered; Gemini, OpenAI, OpenRouter, and Claude displayed local vector marks; provider menu opened and exposed descriptions/check state.
- Follow-up browser verification: seven provider options displayed local vector marks (Gemini, OpenAI, Grok/xAI, Groq, OpenRouter, Claude, and Ollama); only Custom uses a text/API fallback.
- Running app verification on `/app/platforms` and `/app/how-to-use`: all three local platform marks loaded, four How to use step icons rendered, and the removed tour control was absent. Browser console error log was empty.
- Official/source checks used for the local marks included [OpenAI brand guidelines](https://openai.com/brand/), [Google Gemini](https://gemini.google.com/), [Groq](https://groq.com/), and the Simple Icons source records for the remaining compact vectors.
- Five reload checks kept the icon metadata, provider menu, and vector-mark counts valid after hydration. `git diff --check` passed.
- Home browser verification: `Connect API` rendered `data-icon="plug"`; no `data-icon="plus"` remained in that CTA. The project root is `C:\Users\DELL\Desktop\MY PROJECTS\Clipnary`.
- Lordicon reference inspection confirmed the hover-trigger interaction model, but Clipnary does not embed Lordicon JSON or load its runtime CDN. The free Lordicon license requires attribution and imposes CDN/account conditions, so the safer implementation reuses the interaction idea with local vectors and existing icons. See [Lordicon Web docs](https://lordicon.com/docs/web) and [Lordicon licenses](https://lordicon.com/licenses).

Remaining limitations:

- The current browser automation can verify the DOM and computed CSS contract, but it does not expose a reliable pointer-hover primitive for visual capture. Manual pointer hover should still be spot-checked in Chrome.
- Custom is intentionally a text/API fallback because it has no provider brand. The xAI/Grok and Groq marks are compact local vectors tuned for the small picker badge, not wordmark lockups.

## Verified Clipnary rebrand and repository cleanup — 2026-11-18

- Product-facing copy, page titles, email branding, documentation, generated download names, and deployment examples
  now use **Clipnary**.
- The repository folder was moved from its former product-name directory to
  `C:\Users\DELL\Desktop\MY PROJECTS\Clipnary`; the local server was restarted from the new path on port 8766.
- Only generated artifacts were removed: `.tmp_render_check/`, `studio/__pycache__/`, and `tests/__pycache__/`.
  The `data/` folder, database, `.venv/`, source code, tests, and generated user clips were preserved.
- `PEAKCUT_*` environment variables, the default `data/peakcut.db` filename, the session cookie, and the existing
  GitHub repository slug remain as compatibility identifiers. Renaming those without a migration would break
  existing installations, so they are intentionally not treated as product branding.
- Verification: navigation, creation options, highlight ranking, local/no-sign-in behavior, storage, JavaScript
  parsing, queue-load behavior, HTTP 200, and browser console checks passed. The running browser showed Clipnary
  navigation, the centered page layout, API connection state, platform setup, and the Instagram link.

