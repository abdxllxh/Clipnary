# OpusClip Feature Audit

**Date:** 2026-11-16  
**Scope:** Read-only inspection of the authenticated OpusClip Chrome tab, plus the supplied screenshots and public documentation.  
**Safety boundary:** No Create action, paid processing, credit purchase, subscription, upload, or external account change was performed. The account showed 0 credits, so the generated-result/editor workflow could not be opened.

## Evidence labels

- **VERIFIED IN BROWSER** — visibly present in the authenticated OpusClip tab during this audit.
- **VERIFIED IN CODE** — present in the local Clipnary source tree.
- **VERIFIED IN DOCUMENTATION** — supported by an official or primary documentation/licence source.
- **PROPOSED** — a recommended design or implementation direction, not an existing product fact.
- **UNVERIFIED** — not safely accessible in this account/workflow, or not established by the available evidence.

## Observed creation screen

**VERIFIED IN BROWSER:** The selected source was titled “iShowSpeed Reacts To GTA 6 - Official Launch Trailer”, showed a `2k` badge, English speech, Auto genre, and a 3:44 source duration. The page was a recipe/configuration screen with a source preview, summary sidebar, and a disabled Create button because the account had 0 credits.

The key product pattern is clear: OpusClip separates **source selection**, **recipe/effects**, **brand presentation**, and **cost summary** before processing. That separation is worth copying as a product concept; its branding, copy, visual assets, and proprietary implementation should not be copied.

## Feature inventory

| Area | Browser finding | Clipnary implication |
|---|---|---|
| Video import | Source preview, Remove action, speech-language selector, genre selector | Keep Clipnary's URL/upload flow. Add an explicit metadata/preview step only when it does not delay the user's first interaction. |
| Speech language | English selected; a combo box is available | Clipnary currently transcribes locally and can use YouTube captions when available. A user-selected language needs an explicit ASR/translation contract. |
| Genre | Auto selected | **PROPOSED:** treat genre as a ranking hint, not a hard classifier. It can change prompt vocabulary and scoring weights. |
| Adjustable range | Start/end fields and a thumbnail timeline; UI says AI processes only the selected range | Clipnary already has source-range and manual-cut concepts. A proper range slider/timeline is a high-value editor improvement. |
| Aspect/layout | 9:16 selected; 16:9, 1:1, 4:5 also available. For 9:16, seven layouts were shown: Fill, Fit, Split, Three, Four, ScreenShare, Gameplay. Fit has Original, 4:3, and 1:1 crop choices. | Clipnary currently renders local layouts. Add platform presets and scene-aware layout selection later; do not make all layouts a prerequisite for improving clip selection. |
| SRT | Upload SRT action is present | Clipnary has timestamped words and captions. Add SRT import/export as a separate, testable feature. |
| Recipes | “Clip long video” is active. The recipe manager also displayed “Clean up recording”, “Auto-edit talking videos”, “Captions”, “Reframe”, “Social edits”, “AI B-roll”, and “Translate & dub”. | Clipnary's recipe object is a good foundation. Store recipes as versioned JSON and keep effect execution deterministic. |
| Brand kits | No brand kit selected. A popover offered No brand kit, My brand kit, Edit, New brand kit, and Refresh. | Clipnary has creator workspaces; brand presets can sit above clip options without changing the job engine. |
| AI clipping | Clipping switch on; AI picks = Auto. The AI-pick menu showed Auto, ClipAnything (“our smartest model”), and ClipBasic (“great for clipping talking videos”). | This is the largest quality gap. Clipnary's normal-video picker should become a multi-signal candidate/reranking pipeline rather than a single prompt call. |
| User prompt | “Moments to include (optional)” text area and “How to prompt” guidance. Guidance opened a dialog with two instructional video choices; it was not played. | Clipnary should pass a sanitized user instruction into candidate generation/ranking. Never allow video transcript text to override system rules. |
| Clip length | Auto (0m–3m), `<30s`, `30s–59s`, `60s–89s`, `90s–3m`, and `3m–5m` options were visible. | Clipnary currently validates a 5–180 second range for generated options and 3–180 seconds for manual/remake clips. Keep hard limits server-side. |
| Captions | Captions switch on. Initial carousel showed Word Cut, Marker Sweep, Negative keywords, Karaoke, Handwritten, Mozi, and Simple. “View 37 more” opened a gallery of 37 named styles in the visible panel, including Soft Build, Typewriter, Glide, Doodle, Editorial, Retro 3D, Comic, and others. | Clipnary already has caption styles. Add more styles only after a style schema and font/licence inventory are stable. |
| Auto hook | Auto hook Beta switch off. Menu had Viral hook (“animated scroll-stopping hook with motion and SFX”, 2 credits/hook) and Headline (“text title that introduces your video”). Viral hook exposed hook styles such as Montage, Cutaway, Halo, Condensed Italic Serif Title, Cadence, and Hero, plus more. | Clipnary already has hooks/titles. Separate a free local headline/title layer from any future generation-heavy effect. |
| Motion graphics | Beta switch visible and off | **PROPOSED:** implement a small local template set first; treat generative motion graphics as a later resource-heavy category D feature. |
| AI emojis | Switch visible and off | Clipnary already has a local category-to-emoji overlay. Improve mapping and timing before considering a visual-language model. |
| Auto B-roll | Off. Menu showed AI video B-roll (3 free trials, 21 credits/min), AI image B-roll (4 credits/min), and Stock video B-roll (Free). | Local implementation can use user-owned media or stock APIs only with clear licensing. AI-generated B-roll is not free in the observed product and is not required for the MVP. |
| Speech cleanup | Off. Options were Remove pause and Remove filler words. | Clipnary already has local speech cleanup filters, but word deletion needs transcript-aware editing rather than audio filtering alone. |
| Enhance audio | Off | Clipnary has a local compressor/loudness path. It is a useful free baseline, not equivalent to a learned studio enhancement model. |
| Auto SFX | Off | Clipnary currently synthesizes a small local accent sound. This satisfies a free baseline; it is not the same as a licensed SFX library or generative sound design. |
| Auto zoom | Off | Clipnary has a local gentle zoom path. Face-aware reframing is a later visual model task. |
| Auto transitions | Off | Clipnary has local fade in/out transitions. A scene-aware transition system is future work. |
| Auto color correction | Off | Clipnary has a simple local contrast/saturation/gamma adjustment. It should be labelled as a lightweight correction, not professional color grading. |
| Eye-contact correction | Disabled | No conclusion about its implementation or availability can be drawn from this account. |
| Translation/dubbing | Voice dubbing language selector and Caption translation language selector were visible, both off | Caption translation can be local or BYO API. Voice dubbing requires a model/voice licence and much more compute; keep it optional. |
| Summary/cost | Video processing showed 3 credits; clipping and captions showed Free; total 3 credits; Create disabled and “Not enough credits” displayed | Clipnary can show estimates for local CPU/GPU time, ASR duration, and BYO API tokens, but it cannot promise exact provider cost before the provider responds. |
| Rights notice | Page said the user confirms they have rights to use the video | Clipnary should keep a clear rights confirmation and local-use disclaimer. It does not make downloading or reposting copyrighted videos lawful. |

## What could not be verified

**UNVERIFIED:** The following were not safely accessible without spending credits or changing account state:

- Actual generated clip ranking and whether the “ClipAnything” model is better on a given source.
- Generated clip previews, the result library, the timeline editor, manual crop behavior, and re-render behavior.
- Exact processing time, token/model cost, model architecture, scoring formula, and quality metrics.
- Whether every visible toggle works on every source type, language, layout, and account plan.
- Creator discovery/video-library behavior beyond the selected source screen.

The screenshots supplied by the user corroborate the visible recipe, range, caption, hook, and credit-summary patterns, but screenshots cannot prove backend behavior.

## Product lessons for Clipnary

1. **Make the recipe declarative.** A job should store source range, output layouts, caption style, effect flags, prompt, clip count, and model choice as one versioned recipe.
2. **Show a cost/effort estimate before Create.** For local work, show “estimated CPU/GPU time” and disk space. For a BYO provider, show an estimate only when the provider exposes enough information; label it as an estimate.
3. **Keep generation additive.** “Find more” must append new clip IDs and preserve old outputs. Clipnary already follows this pattern in code.
4. **Separate free local effects from paid/model-dependent effects.** Captions, trim, crop, simple zoom, color, compression, fades, and synthetic SFX can run locally. B-roll, dubbing, eye-contact correction, and strong visual understanding require a different model/resource class.
5. **Quality beats clip count.** A “top 3 strong moments” mode is more valuable than returning 12 generic clips.

## Audit conclusion

**VERIFIED IN BROWSER:** OpusClip's creation UX is a configurable recipe builder with range selection, AI model choices, captions, hooks, visual/audio effects, translation, brand kits, and a credit summary.

**PROPOSED:** Clipnary can reproduce the useful product structure with free local components, but it should not claim parity with OpusClip's proprietary multimodal models. The honest target for the next milestone is: reliable local clipping, better multi-signal ranking, a real timeline editor, deterministic local effects, and transparent BYO-provider accounting.

