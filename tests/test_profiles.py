"""Deterministic checks for public source metadata enrichment."""
import sys
import types
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio import profiles  # noqa: E402


class FakeYDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=False):
        assert download is False
        assert self.options["skip_download"] is True
        return {
            "view_count": 123456,
            "timestamp": 1763337600,
            "duration": 42,
            "thumbnail": "https://example.test/thumb.jpg",
            "title": "Public VOD",
            "webpage_url": url,
        }


fake_yt_dlp = types.SimpleNamespace(YoutubeDL=FakeYDL)
got = profiles._video_metadata("https://kick.com/example/videos/vod-123", fake_yt_dlp)

checks = {
    "view count is preserved": got.get("views") == 123456,
    "timestamp is preserved": got.get("timestamp") == 1763337600,
    "duration is preserved": got.get("duration") == 42,
    "thumbnail is preserved": got.get("thumbnail") == "https://example.test/thumb.jpg",
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)


class FakePlaylistYDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=False):
        assert download is False
        assert self.options["extract_flat"] is True
        now = int(time.time())
        platform = "twitch" if "twitch.tv" in url else "kick"
        if platform == "twitch":
            entry = {"id": "v2929044358", "title": "Twitch VOD", "timestamp": now - 3600,
                     "duration": 60, "view_count": 9876, "thumbnail": "https://example.test/twitch.jpg",
                     "webpage_url": "https://www.twitch.tv/videos/2929044358"}
        else:
            entry = {"id": "vod-123456789", "title": "Kick VOD", "timestamp": now - 7200,
                     "duration": 90, "view_count": 5432, "thumbnail": "https://example.test/kick.jpg",
                     "webpage_url": "https://kick.com/example/videos/vod-123456789"}
        return {"entries": [entry], "id": "source"}


old_yt_dlp = sys.modules.get("yt_dlp")
sys.modules["yt_dlp"] = types.SimpleNamespace(YoutubeDL=FakePlaylistYDL)
try:
    twitch = profiles.recent_videos("https://www.twitch.tv/example", force=True)
    kick = profiles.recent_videos("https://kick.com/example", force=True)
finally:
    if old_yt_dlp is None:
        sys.modules.pop("yt_dlp", None)
    else:
        sys.modules["yt_dlp"] = old_yt_dlp

platform_checks = {
    "Twitch public VODs are returned": twitch["videos"][0]["platform"] == "Twitch" and twitch["videos"][0]["views"] == 9876,
    "Kick public VODs are returned": kick["videos"][0]["platform"] == "Kick" and kick["videos"][0]["views"] == 5432,
}
failed.extend(name for name, ok in platform_checks.items() if not ok)
for name, ok in platform_checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print("ALL PASSED" if not failed else f"{len(failed)} failed")
raise SystemExit(1 if failed else 0)
