"""Test suite verifying the Streamers live page contract and endpoints."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from studio import db
from studio.server import app
import studio.streamers as streamers

db.init()
client = TestClient(app, base_url="http://127.0.0.1:8765")
html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
compact_html = re.sub(r"\s+", "", html)

fails = []

def has(pattern: str) -> bool:
    if pattern in html:
        return True
    return re.sub(r"\s+", "", pattern) in compact_html

def check(name: str, ok: bool):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)

# 1. Backend Endpoint Tests
res = client.get("/api/streamers/live")
check("backend /api/streamers/live returns 200 OK", res.status_code == 200)

data = res.json()
streamer_list = data.get("streamers", [])
check("backend returns at least 20 live streamers", len(streamer_list) >= 20)

# Verify sorting descending by viewer count
viewers = [s.get("viewers", 0) for s in streamer_list]
check("streamers list is sorted descending by viewer count", viewers == sorted(viewers, reverse=True))

# Verify all 3 major streaming platforms are present
all_streamers = data.get("streamers", []) + data.get("offline_streamers", [])
platforms = {s.get("platform_key") for s in all_streamers}
check("streamers catalog includes kick, twitch, and youtube", {"kick", "twitch", "youtube"}.issubset(platforms))

# Verify top streamers from user screenshot and prompt
names = {s.get("name") for s in all_streamers}
for expected_name in ("StableRonaldo", "Kai Cenat", "IShowSpeed", "Adin Ross", "Asmongold", "HasanAbi", "Jynxzi", "N3on", "PlaqueBoyMax", "Marlon"):
    check(f"catalog includes streamer {expected_name}", expected_name in names)

# Verify live streamers viewer threshold (>= 25 viewers)
for s in streamer_list:
    check(f"{s['name']} has >= 25 viewers", int(s.get("viewers") or 0) >= 25 and s.get("is_live") is not False)

# Verify Adin Ross offline status
adin = next((s for s in all_streamers if s.get("id") == "adinross"), None)
check("Adin Ross is categorized as offline", adin is not None and (adin.get("is_live") is False or adin.get("viewers") == 0))
check("offline_streamers list contains Adin Ross", any(s.get("id") == "adinross" for s in data.get("offline_streamers", [])))

# Check StableRonaldo metadata matches screenshot
sr = next((s for s in streamer_list if s.get("name") == "StableRonaldo"), None)
check("StableRonaldo has ~50,695 viewers", sr is not None and sr.get("viewers") == 50695)
check("StableRonaldo has GTA 6 trailer title", sr is not None and "GTA 6" in sr.get("title", ""))
check("StableRonaldo has valid channel URL", sr is not None and "twitch.tv" in sr.get("channel_url", ""))

# Verify upcoming_streamers and streamed_today lists in backend
check("backend returns upcoming_streamers list", len(data.get("upcoming_streamers", [])) >= 3)
check("backend returns streamed_today list", len(data.get("streamed_today", [])) >= 3)
for s in data.get("upcoming_streamers", []):
    check(f"upcoming streamer {s['name']} has scheduled_time and channel_url", bool(s.get("scheduled_time") and s.get("channel_url")))
for s in data.get("streamed_today", []):
    check(f"streamed today {s['name']} has ended_ago and peak_viewers", bool(s.get("ended_ago") and s.get("peak_viewers")))

# Test filtering
res_speed = client.get("/api/streamers/live?q=speed")
check("search query 'speed' finds IShowSpeed", res_speed.status_code == 200 and any("Speed" in s["name"] for s in res_speed.json().get("streamers", [])))

res_kick = client.get("/api/streamers/live?platform=kick")
check("platform filter 'kick' returns only Kick streams", res_kick.status_code == 200 and all(s["platform_key"] == "kick" for s in res_kick.json().get("streamers", [])))

res_gaming = client.get("/api/streamers/live?category=gaming")
check("category filter 'gaming' returns only Gaming streams", res_gaming.status_code == 200 and all("gaming" in s["category"].lower() for s in res_gaming.json().get("streamers", [])))

# 2. Frontend Contract Tests
check("ROUTES defines streamers route", has('streamers: "streamers"'))
check("topbar mainnav has Streamers link with LIVE badge", has('topLink("streamers", "radio", "Streamers", \'<span class="nav-count live-pill">LIVE</span>\')'))
check("sidebar nav has Streamers link", has('nav("streamers", navIc("radio", "streamers"), "Streamers"'))
check("view switcher handles streamers page container", has('v === "streamers"') and has('id="streamers-page"'))
check("render function calls drawStreamersPage", has('if (S.view === "streamers") drawStreamersPage();'))
check("drawStreamersPage function exists", has('function drawStreamersPage()'))
check("loadStreamers function exists", has('async function loadStreamers('))
check("search bar is removed from streamers view as requested", not has('<input id="streamer_search"'))
check("language filter is removed from streamers view as requested", not has('<select id="streamer_lang"'))
check("Everything/All category pill is removed as requested", not has('data-v="all">Everything</button>'))
check("platform pills are present (Twitch, Kick, YouTube)", has('data-v="twitch"') and has('data-v="kick"') and has('data-v="youtube"'))
check("category pills are present (Gaming, Just Chatting)", has('data-v="gaming"') and has('data-v="just chatting"'))
check("Refresh button exists", has('data-act="refreshstreamers"'))
check("trending live header is present", has('Trending live now'))
check("MORE LIVE NOW section is present", has('MORE LIVE NOW'))
check("All Live Streams heading is removed as requested", not has('All Live Streams'))

# 3. Two Dedicated Bottom Divs
check("Div 1: Scheduled to be Live Today exists", has('id="streamers-scheduled-div"') and has('Scheduled to be Live Today'))
check("Div 1: includes stream links", has('sched-time-pill') and has('title="Open channel stream link"'))
check("Div 2: Streamed Earlier Today exists", has('id="streamers-streamed-today-div"') and has('Streamed Earlier Today'))
check("Div 2: includes ended metrics and peak viewers", has('streamed-metrics-tag') and has('Peak:'))

# 4. Hero Actions: Copy Clip URL, Copy Stream URL, Start Clipping, Add to Creators
check("copy clip URL action exists", has('data-act="copyclipurl"'))
check("copy clip URL button text exists", has('Copy Clip URL'))
check("copy stream URL action exists", has('data-act="copystreamurl"'))
check("copy stream URL button text exists", has('Copy Stream URL'))
check("clipboard copy logic is implemented with feedback toast", has('navigator.clipboard.writeText') and has('Stream URL copied'))
check("clip live stream action exists", has('data-act="cliplive"'))
check("clip live stream button text exists", has('Start Clipping'))
check("add to creators action exists", has('data-act="addstreamertocreator"'))
check("add to creators button text exists", has('Add to Creators'))
check("preview and watch player switching action exists", has('data-act="pickstream"'))

print("ALL STREAMERS TESTS PASSED" if not fails else f"{len(fails)} failed")
raise SystemExit(1 if fails else 0)
