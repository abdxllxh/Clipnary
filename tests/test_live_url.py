"""Test live URL detection, live preview, and live stream clipping pipeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from unittest.mock import MagicMock, patch
from studio import media, jobs

def test_normalize_url():
    assert media.normalize_url("https://www.youtube.com/@somecreator") == "https://www.youtube.com/@somecreator/live"
    assert media.normalize_url("https://www.youtube.com/@somecreator/live") == "https://www.youtube.com/@somecreator/live"
    assert media.normalize_url("https://www.youtube.com/watch?v=12345678901") == "https://www.youtube.com/watch?v=12345678901"
    assert media.normalize_url("https://twitch.tv/streamer") == "https://twitch.tv/streamer"
    assert media.normalize_url("https://kick.com/streamer") == "https://kick.com/streamer"
    print("PASS normalize_url handles standard and live URLs")


def test_preview_live():
    mock_info = {
        "title": "24/7 Live Stream Reaction",
        "uploader": "LiveCreator",
        "description": "Streaming live now!",
        "duration": 0,
        "is_live": True,
        "thumbnail": "",
        "kind": "video"
    }
    with patch("studio.media.info", return_value=mock_info):
        prev = media.preview("https://www.youtube.com/@livecreator/live")
        assert prev["is_live"] is True
        assert prev["title"] == "24/7 Live Stream Reaction"
        assert prev["uploader"] == "LiveCreator"
    print("PASS media.preview accepts live URLs without throwing ValueError")


def test_youtube_bot_check_is_not_reported_as_cookie_login():
    """yt-dlp's bot-check suggestion must not be mistaken for a cookie read failure."""
    url = "https://www.youtube.com/live/qSyo5d-dVzA"
    error = RuntimeError(
        "Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication."
    )
    old_pause = media._yt_refused_until
    media._yt_refused_until = 0
    try:
        try:
            with media._youtube_guard(url):
                raise error
        except media.YouTubeBlocked as exc:
            assert "bot check" in str(exc)
            assert "browser's YouTube login" not in str(exc)
        else:
            raise AssertionError("YouTube bot-check was not classified as YouTubeBlocked")
    finally:
        media._yt_refused_until = old_pause
    print("PASS YouTube bot-check errors are not mislabeled as cookie-login errors")


def test_jobs_live_handling(tmp_path):
    job_dir = tmp_path / "job_live"
    job_dir.mkdir(parents=True, exist_ok=True)
    fake_job = {
        "id": "job-live-1",
        "creator": "c1",
        "dir": str(job_dir),
        "source": {"type": "url", "url": "https://www.youtube.com/watch?v=live1234567"},
        "options": jobs.clean_options({"range_start": 0, "range_end": 600, "max_clips": 3}),
        "status": "queued",
        "title": "Initial",
        "clips": [],
        "user": "local"
    }
    mock_meta = {
        "title": "Live Broadcast Today",
        "uploader": "TestStreamer",
        "kind": "video",
        "duration": 0,
        "is_live": True,
        "live_status": "is_live",
        "live_started_at": 1000,
        "live_elapsed": 600.0
    }
    # Mock the bounded live-history download and exercise the elapsed-window progress callback.
    live_progress = []
    def fake_download(url, job_dir, duration=600, height=720, cancel=None, on_progress=None):
        out_path = Path(job_dir) / "source.mp4"
        if on_progress:
            on_progress(0.5)
            live_progress.append(0.5)
        out_path.write_bytes(b"dummy video data " * 100)
        return out_path

    # Verify that jobs._run does not raise RuntimeError("This link is a live stream...")
    with patch("studio.media.info", return_value=mock_meta), \
         patch("studio.media.save_thumb", return_value=True), \
         patch("studio.media.download_live_from_start", side_effect=fake_download), \
         patch("studio.media.probe", return_value={"width": 1280, "height": 720, "duration": 600.0}), \
         patch("studio.media.extract_audio", return_value=None), \
         patch("studio.media.load_audio", return_value=[0] * 160000), \
         patch("studio.media.loudness_per_second", return_value=MagicMock(tolist=lambda: [-20.0] * 10)), \
         patch("studio.transcribe.transcribe", return_value=[{"w": "hello", "s": 1.0, "e": 2.0}]), \
         patch("studio.brain.find_clips", return_value=[]), \
         patch("studio.usage.set_context", return_value=None), \
         patch("studio.jobs.save", return_value=None):
        jobs._run_job(fake_job)
        assert fake_job.get("is_live") is True
        assert fake_job.get("status") == "done"
        assert live_progress == [0.5]
    print("PASS jobs._run processes live stream URL to completion without raising error")


def test_ui_live_elements():
    html = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")
    assert "CURRENTLY LIVE" in html
    assert "live-stream-badge" in html
    assert "live-callout" in html
    assert "live-dot pulse" in html
    assert "is-live" in html
    assert "live for" in html
    assert "err.status = r.status" in html
    assert "const definitive = e?.status === 422 || e?.status === 503" in html
    assert "attempts === 1" in html
    assert "That link is already listed" in html
    print("PASS web/index.html includes all live indicator badges, pulsing dots, and callouts")


if __name__ == "__main__":
    import tempfile
    test_normalize_url()
    test_preview_live()
    test_youtube_bot_check_is_not_reported_as_cookie_login()
    with tempfile.TemporaryDirectory() as td:
        test_jobs_live_handling(Path(td))
    test_ui_live_elements()
    print("ALL LIVE URL TESTS PASSED")
