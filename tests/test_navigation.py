"""Focused contract checks for the visible navigation, live indicator, and existing clip editor wiring."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
server = (ROOT / "studio" / "server.py").read_text(encoding="utf-8")
compact_html = re.sub(r"\s+", "", html)

fails = []


def has(pattern: str) -> bool:
    if pattern in html:
        return True
    return re.sub(r"\s+", "", pattern) in compact_html


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)


for marker in (
    'id="mainnav"',
    'topLink("howto", "bulb", "How to use")',
    'topLink("library"',
    'topLink("platforms"',
    'topLink("creators", "users", "Creators")',
    'class="topbar-center"',
    'class="social-link"',
    'ROUTES = {howto: "how-to-use", overview: "", library: "videos", creators: "creators"',
    'id="creator-directory"',
    'Open creator workspace',
    'data-act="newcreator"',
    'data-tab="clips"',
    'data-act="delcreatorid"',
    'API connection',
    'How to connect your apps',
    'recent-skeleton',
    'https://console.cloud.google.com/apis/credentials',
    'https://developers.facebook.com/apps',
    'https://developers.tiktok.com/apps',
    'Select your AI model',
    'No activity yet',
    'Model not selected',
    'https://www.instagram.com/abdullahdev.co/',
):
    check(f"top navigation exposes {marker}", has(marker))

check("Settings is not exposed as a top navigation item", not has('topLink("settings"'))
check("Post Queue is not exposed as a top navigation item", not has('topLink("queue"'))
check("Global destinations include How to use, Home, library, creators and platforms", all(has(marker) for marker in ('topLink("howto", "bulb", "How to use")', 'topLink("overview", "home", "Home")', 'topLink("library"', 'topLink("creators", "users", "Creators")', 'topLink("platforms"')))
check("Creators is a plain destination without a header dropdown", has('topLink("creators", "users", "Creators")') and not has('data-act="togglecreators"') and not has('creator-toggle'))
check("How to use has its own routed page", has('function drawHowTo') and has('id="howto"') and has('S.view === "howto"'))
check("Interactive tour entry point is removed", not has('data-act="tour"') and not has('Take the interactive tour') and not has('Take the tour'))
check("Main navigation has a centered responsive layout", has('grid-template-columns:minmax(190px,1fr) auto minmax(190px,1fr)') and has('grid-column:2;grid-row:1') and has('.app .topbar .mainnav{position:static'))
check("Creator header reserves separate workspace and global-nav rows", has('grid-template-rows:44px 46px') and has('grid-column:1/-1;grid-row:2'))
check("Creator tab indicator stays inside its tab strip", has('.utabs{position:relative') and has('.utabs .ind{position:absolute'))
check("Platform cards use local brand marks", all(has(marker) for marker in ('/brand/youtube-mark.svg', '/brand/instagram-mark.svg', '/brand/tiktok-mark.svg')))
check("Buttons and cards have scoped interaction states", has('.app .btn.primary:hover') and has('.app .appcard:hover') and has('@keyframes clipnary-in'))
check("Upload control follows the dark app theme", has('.app .composer.compact .chip') or has('background:var(--muted)'))
check("New dashboards have an activity empty state", has('const hasActivity = Boolean') and has('No activity yet'))
check("New dashboards gate usage on model selection", has('if (!k.ready && !hasRecords)') and has('Select your AI model'))
check("Home no longer renders the removed setup cards", not has('function nextSteps'))
check("YouTube troubleshooting controls are not in the visible platform page", not has('YouTube link access</h2>') and not has('id="yt_browser"'))
check("Creator save dialog has a visible saving state", has('dialog-saving') and has('Saving creator'))
check("New creators require a channel URL", has('id="nc_chan"') and has('required autofocus'))
check("Creators without a URL get a setup action", has('Open creator setup') and has('data-act="tab" data-t="setup"'))
check("API usage has a guarded reset action", has('data-act="resetusage"') and has('Reset API usage?'))
check("API provider uses a branded custom picker", all(has(marker) for marker in (
    'id="ai_provider_button"', 'id="ai_provider_menu"', 'data-act="providerselect"',
    'class="provider-option"', 'class="provider-native"', 'providerDescriptions'
)))
check("API provider picker preserves native form compatibility", has('sel.dispatchEvent(new Event("change", {bubbles:true}))') and has('drawProviderPicker(S.ai)'))
check("Interactive local icons expose the hover contract", all(has(marker) for marker in (
    'data-icon="${esc(n)}"',
    '@keyframes icon-hover-colour',
    '.btn:hover [data-icon]',
)))
check("Provider marks use local vectors with text fallbacks", all(has(marker) for marker in (
    'const providerLogoPaths =',
    'provider-icon svg',
    'providerLogoPaths[p.id] ?',
    'xai:',
    'groq:',
    'ollama:',
    '.provider-option:hover .provider-icon svg',
)))
check("API action buttons carry meaningful local icons", all(has(marker) for marker in (
    '${ic("check")}Save and test',
    '${ic("bolt")}Test again',
    '${ic("trash")}Remove API key',
)))
check("API connection CTAs use a connection mark instead of a generic plus", has('${ic("plug")}Connect API') and not has('${ic("plus")}Connect API'))

check("live stream indicator exposes CURRENTLY LIVE status", has('CURRENTLY LIVE') and has('is-live') and has('live-stream-badge'))

for marker in (
    'data-act="openclip"',
    'data-act="delclip"',
    'data-act="remake"',
    'data-f="start"',
    'data-f="end"',
):
    check(f"clip editor exposes {marker}", has(marker))

check("clip editor hides the removed picture adjustment controls", "<h3>Picture adjustments</h3>" not in html
      and 'data-f="color_brightness"' not in html.split('function drawClipDlg')[1].split('function render')[0])

check("recipe create button starts clip generation", 'if (a === "recipecreate")' in html and 'await startMakeClips()' in html)
check("recipe create requires usage permission", 'Please confirm that you have permission' in html)
check("recipe cancel button closes the editor", 'if (a === "recipecancel")' in html)

for marker in (
    '@app.get("/api/apps")',
    '@app.get("/oauth/{platform}/start")',
    '@app.get("/oauth/{platform}/callback")',
    '@app.post("/api/bulk/delete")',
    '@app.post("/api/usage/reset")',
    '@app.get("/api/creators/{cid}/recent-videos")',
):
    check(f"backend keeps {marker}", marker in server)

profiles = (ROOT / "studio" / "profiles.py").read_text(encoding="utf-8")
check("recent creator videos use real flat platform extraction", 'def recent_videos(' in profiles and 'extract_flat' in profiles and 'platform not in ("YouTube", "Twitch", "Kick")' in profiles)
check("recent creator videos expose public upload timestamps", 'feeds/videos.xml?channel_id=' in profiles and '"timestamp"' in profiles)
check("recent creator videos normalize bare channel URLs", 'if "://" not in url' in profiles and 'url = "https://" + url' in profiles)
check("recent creator refresh bypasses cached data", 'force: bool = False' in profiles and 'force=bool(refresh)' in server)
check("creator video cards include copy and reuse", has('data-act="copyurl"') and has('data-act="useurl"'))
check("creator video actions have click handlers", 'if (a === "copyurl")' in html and 'if (a === "useurl")' in html)
check("copy link has a clipboard fallback", 'document.execCommand("copy")' in html)
check("workspace tabs stay in the centered header cluster", has('class="topbar-center"'))
check("creator thumbnails preserve the complete source image responsively", has('aspect-ratio:16/9') and has('grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))'))
check("creator feed includes YouTube uploads, streams, Shorts and platform VODs", 'base_url + suffix for suffix in ("/videos", "/streams", "/shorts")' in profiles and 'else [base_url + "/videos"]' in profiles)
check("creator setup exposes public Twitch and Kick sources", has('data-act="chadd"'))
check("live recording backend is explicitly paused", 'LIVE_RECORDING_ENABLED = False' in (ROOT / "studio" / "live.py").read_text(encoding="utf-8") and 'Live recording is disabled right now.' in (ROOT / "studio" / "live.py").read_text(encoding="utf-8"))
check("AI settings expose a safe remove-key action", has('data-act="airemove"') and 'remove_key' in server and 'new_key != ""' in (ROOT / "studio" / "ai.py").read_text(encoding="utf-8"))
check("API usage links back to API connection", has('data-v="settings" data-tab="ai"'))
check("usage chart is a seven-day daily view", has('daily_7 || k.daily') and has('last 7 days') and has('Today and the previous 6 days'))
check("usage bars expose exact accessible details", has('class="usage-bar"') and has('aria-label="${esc(detail)}"') and has('Hover a bar for the exact tokens and calls.'))
check("recent creator videos have working metadata filters", all(has(marker) for marker in ('data-act="recentfilter"', 'data-recent-filter="query"', 'data-recent-filter="date"', 'data-recent-filter="duration"', 'data-recent-filter="sort"', 'data-act="recentapply"', 'function filteredRecentVideos')))

print("ALL PASSED" if not fails else f"{len(fails)} failed")
raise SystemExit(1 if fails else 0)
