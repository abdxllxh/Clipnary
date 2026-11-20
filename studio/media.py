"""Getting video in: link download, probing, audio extraction, loudness."""
import contextlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from . import config

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_POT_PROCESS = None
_POT_LOCK = threading.Lock()
_POT_HOST = "127.0.0.1"
_POT_PORT = 4416


def ensure_youtube_pot_provider() -> bool:
    """Start the local yt-dlp PO-token provider when it is installed.

    YouTube now gates many media formats behind per-video Proof-of-Origin tokens. The provider is local-only and
    optional: when it is absent, non-YouTube sources and older YouTube responses continue to work normally.
    """
    global _POT_PROCESS
    if str(os.environ.get("PEAKCUT_YOUTUBE_POT", "1")).strip() == "0":
        return False
    try:
        with socket.create_connection((_POT_HOST, _POT_PORT), timeout=0.15):
            return True
    except OSError:
        pass
    with _POT_LOCK:
        try:
            with socket.create_connection((_POT_HOST, _POT_PORT), timeout=0.15):
                return True
        except OSError:
            pass
        root = Path(os.environ.get("PEAKCUT_POT_PROVIDER_DIR") or Path.home() / "bgutil-ytdlp-pot-provider") / "server"
        script = root / "build" / "main.js"
        node = shutil.which("node")
        if not node or not script.is_file():
            return False
        try:
            _POT_PROCESS = subprocess.Popen([node, str(script)], cwd=str(root), stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                try:
                    with socket.create_connection((_POT_HOST, _POT_PORT), timeout=0.15):
                        return True
                except OSError:
                    time.sleep(0.2)
        except OSError:
            _POT_PROCESS = None
    return False

# ---------------------------------------------------------------- when YouTube refuses this server
# YouTube sometimes refuses a server's downloads altogether ("sign in to confirm you're not a bot"). It is a
# refusal of the server, not of one video, so once it happens YouTube links are turned away at once for a few
# minutes, with a clear message, instead of each one waiting to fail. Then the next link simply tries again.
YT_PAUSE = 600
_yt_refused_until = 0.0
YT_BLOCKED = ("This YouTube link is valid, but YouTube is currently blocking Clipnary's local downloader with a bot "
              "check. The live video may still play in Chrome. Try again later, or upload the video file instead.")
YT_COOKIE_HELP = ("Clipnary couldn't read the selected browser's YouTube login. Close that browser completely, make "
                  "sure you are signed in and age-verified on YouTube, then try again. You can also upload the video "
                  "file instead.")
YT_DPAPI_HELP = ("Windows couldn't decrypt the selected browser's saved YouTube cookies. Browser login is unavailable "
                 "on this computer. The reliable path is to upload the video file instead; browser-cookie troubleshooting "
                 "is available only to local server operators.")
YT_AGE_HELP = ("This YouTube video is age-restricted. It may play in your browser but still be unavailable to the "
                "local downloader. Try the local browser troubleshooting options only if you administer Clipnary; otherwise "
                "upload the video file instead.")
_BOT_CHECK = re.compile(r"not a bot|confirm you.?re not|sign in to confirm(?! your age)", re.I)
# Do not match the word "cookies" by itself. yt-dlp includes the generic
# ``--cookies-from-browser`` suggestion in bot-check errors, which is not the
# same thing as Clipnary failing to decrypt or read a configured cookie source.
_COOKIE_CHECK = re.compile(r"failed to load cookies|could not copy cookies|error decrypting cookies|cookie database|cookie file", re.I)
_DPAPI_CHECK = re.compile(r"dpapi|decrypt", re.I)
_AGE_CHECK = re.compile(r"sign in to confirm your age|age-restricted|age restricted", re.I)


class YouTubeBlocked(RuntimeError):
    pass


class YouTubeAccessError(RuntimeError):
    """A YouTube video needs an authenticated local browser session or another access fix."""
    pass


def is_youtube(url: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse((url or "").strip()).hostname or "").lower()
    return host in ("youtube.com", "youtu.be") or host.endswith((".youtube.com", ".youtu.be"))


def youtube_paused() -> bool:
    return time.time() < _yt_refused_until


def check_youtube(url: str):
    """Raise YouTubeBlocked straight away if YouTube is refusing this server right now."""
    if is_youtube(url) and youtube_paused():
        raise YouTubeBlocked(YT_BLOCKED)


def note_refusal(url: str, err) -> bool:
    """If this error is YouTube refusing the server, pause YouTube links for a while. True if it was."""
    global _yt_refused_until
    if is_youtube(url) and _BOT_CHECK.search(str(err)):
        _yt_refused_until = time.time() + YT_PAUSE
        return True
    return False


def note_cookie_error(url: str, err) -> bool:
    """Turn a browser-cookie failure into a useful local setup message."""
    return is_youtube(url) and _COOKIE_CHECK.search(str(err)) is not None


@contextlib.contextmanager
def _youtube_guard(url):
    check_youtube(url)
    try:
        yield
    except YouTubeBlocked:
        raise
    except Exception as e:  # noqa: BLE001
        if is_youtube(url) and _AGE_CHECK.search(str(e)):
            raise YouTubeAccessError(YT_AGE_HELP) from None
        if is_youtube(url) and _DPAPI_CHECK.search(str(e)):
            raise YouTubeAccessError(YT_DPAPI_HELP) from None
        if note_refusal(url, e):
            raise YouTubeBlocked(YT_BLOCKED) from None
        if note_cookie_error(url, e):
            raise YouTubeAccessError(YT_COOKIE_HELP) from None
        raise


def site_allowed(url: str) -> bool:
    """Links are fetched by the server, so only known video sites are accepted (never arbitrary addresses)."""
    from urllib.parse import urlparse
    try:
        u = urlparse(url.strip())
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme in ("http", "https") and any(host == s or host.endswith("." + s) for s in config.ALLOWED_SITES)


def run(cmd, cwd=None, timeout=3600, cancel=None, on_progress=None):
    """Run a media command while allowing the caller to stop it.

    ffmpeg can spend minutes inside one encode, so a flag checked only between
    pipeline stages is not enough for a responsive Cancel button.  The small
    polling loop lets the worker terminate the child process as soon as the
    user asks.
    """
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    began = time.monotonic()
    last_progress = began
    stdout = stderr = None
    try:
        while True:
            if cancel is not None and cancel.is_set():
                p.kill()
                stdout, stderr = p.communicate()
                raise RuntimeError("cancelled")
            left = timeout - (time.monotonic() - began)
            if left <= 0:
                p.kill()
                stdout, stderr = p.communicate()
                raise RuntimeError(f"{Path(str(cmd[0])).name} took too long and was stopped.")
            now = time.monotonic()
            if on_progress and now - last_progress >= 2:
                try:
                    on_progress(now - began)
                except Exception:
                    pass
                last_progress = now
            try:
                # communicate() drains stdout/stderr while waiting. A poll loop that never drains these pipes can
                # deadlock ffmpeg/ffprobe on Windows even when the command itself has already finished.
                stdout, stderr = p.communicate(timeout=min(0.2, left))
                break
            except subprocess.TimeoutExpired:
                continue
    finally:
        if stdout is None:
            p.kill()
            stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"{Path(str(cmd[0])).name} failed: {stderr[-1500:]}")
    return stdout


class _Quiet:
    def debug(self, m): pass
    def info(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass


def youtube_cookie_options(url: str = "") -> dict:
    """Return an optional browser-cookie setting without ever exposing or storing the cookies.

    This is intentionally opt-in and useful only when Clipnary runs on the same computer/user as the browser.
    """
    if not is_youtube(url):
        return {}
    try:
        from . import accounts
        s = accounts.settings()
        browser = str(s.get("youtube_browser") or "").strip().lower()
        profile = str(s.get("youtube_profile") or "").strip() or None
        cookie_file = str(s.get("youtube_cookie_file") or "").strip()
    except Exception:  # no user context, or settings are unavailable during a standalone call
        browser, profile, cookie_file = "", None, ""
    if cookie_file:
        p = Path(cookie_file).expanduser()
        if not p.is_file():
            raise YouTubeAccessError("Clipnary couldn't find the selected cookies.txt file. Use the local browser troubleshooting option or upload the video file instead.")
        return {"cookiefile": str(p.resolve())}
    if browser == "waterfox":
        import os
        root = Path(os.environ.get("APPDATA", "")) / "Waterfox" / "Profiles"
        profiles = [p for p in root.glob("*") if p.is_dir() and (p / "cookies.sqlite").is_file()]
        if not profiles:
            raise YouTubeAccessError("Clipnary couldn't find a Waterfox profile. Sign in to YouTube in Waterfox once, then retry.")
        profile = max(profiles, key=lambda p: (p / "cookies.sqlite").stat().st_mtime)
        # Waterfox stores Firefox-compatible cookies, so yt-dlp's Firefox reader can load this profile directly.
        return {"cookiesfrombrowser": ("firefox", str(profile), None, None)}
    if browser not in ("chrome", "edge", "firefox", "brave"):
        return {}
    return {"cookiesfrombrowser": (browser, profile, None, None)}


def browser_profiles(browser: str = "chrome") -> list:
    """Names of Chromium profiles on this computer, without reading cookies or browsing history."""
    import os
    roots = {"chrome": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
             "edge": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
             "brave": Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "User Data"}
    root = roots.get(str(browser or "").strip().lower())
    if not root or not root.is_dir():
        return []
    try:
        state = json.loads((root / "Local State").read_text(encoding="utf-8"))
        info = ((state.get("profile") or {}).get("info_cache") or {})
        out = []
        for directory, item in info.items():
            if re.fullmatch(r"[A-Za-z0-9 _.-]{1,80}", directory or ""):
                out.append({"directory": directory, "name": str((item or {}).get("name") or directory)[:80]})
        return sorted(out, key=lambda x: (x["directory"] != "Default", x["directory"].lower()))
    except (OSError, ValueError, AttributeError):
        return []


def _ydl(opts, url=""):
    import yt_dlp
    if is_youtube(url):
        ensure_youtube_pot_provider()
    # a channel or playlist link is answered as "a list" straight away, never walked video by video
    return yt_dlp.YoutubeDL({"noplaylist": True, "quiet": True, "no_warnings": True, "logger": _Quiet(),
                             "extract_flat": "in_playlist", "playlistend": 1, "socket_timeout": 20,
                             "concurrent_fragment_downloads": 4, **youtube_cookie_options(url), **opts})


def _video_format(height):
    return f"bv*[height<={height}][vcodec^=avc1]+ba[ext=m4a]/bv*[height<={height}]+ba/b[height<={height}]/b"


def _biggest(job_dir: Path, stem: str) -> Path:
    files = sorted((p for p in job_dir.glob(stem + ".*") if p.suffix not in (".part", ".ytdl")),
                   key=lambda p: p.stat().st_size, reverse=True)
    if not files:
        raise RuntimeError("Download finished but no file was produced.")
    return files[0]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/(?:@[^/?#]+|channel/[^/?#]+|c/[^/?#]+))/?(?:[?#].*)?$", url)
    return m.group(1) + "/live" if m else url


def info(url: str) -> dict:
    """Title, channel and length, without downloading anything."""
    norm_url = normalize_url(url)
    with _youtube_guard(norm_url), _ydl({}, norm_url) as ydl:
        try:
            i = ydl.extract_info(norm_url, download=False)
        except Exception:
            if norm_url != url:
                with _youtube_guard(url), _ydl({}, url) as ydl2:
                    i = ydl2.extract_info(url, download=False)
            else:
                raise
    live_status = str(i.get("live_status") or "").strip().lower()
    is_live = bool(i.get("is_live") or live_status in ("is_live", "post_live"))
    try:
        live_started_at = float(i.get("release_timestamp") or 0) or None
    except (TypeError, ValueError):
        live_started_at = None
    live_elapsed = 0.0
    if live_status == "is_live" and live_started_at:
        live_elapsed = max(0.0, time.time() - live_started_at)
    raw_views = i.get("view_count")
    try:
        views = int(raw_views) if raw_views is not None else None
    except (TypeError, ValueError):
        views = None
    return {"title": i.get("title") or "", "uploader": i.get("uploader") or i.get("channel") or "",
            "description": str(i.get("description") or "")[:600],
            "duration": float(i.get("duration") or 0), "is_live": is_live,
            "live_status": live_status, "live_started_at": live_started_at,
            "live_elapsed": live_elapsed,
            "views": views,
            "thumbnail": i.get("thumbnail") or "", "kind": i.get("_type") or "video"}


def youtube_words(url: str):
    """YouTube's own transcript of a video, word by word: ([{'w', 's', 'e'}, ...], language), or None if the video
    has none. Only the transcript in the language that was spoken is used, never a translation."""
    if not is_youtube(url):
        return None
    import json
    with _youtube_guard(url), _ydl({}, url) as ydl:
        i = ydl.extract_info(url, download=False)
        auto = i.get("automatic_captions") or {}
        key = next((k for k in auto if k.endswith("-orig")), None)
        if not key and i.get("language") in auto:
            key = i["language"]
        track = next((f for f in auto.get(key) or [] if f.get("ext") == "json3" and f.get("url")), None) if key else None
        if not track:
            return None
        raw = ydl.urlopen(track["url"]).read(40_000_000)
    return _caption_words(json.loads(raw)), key.replace("-orig", "")


def youtube_english_words(url: str):
    """YouTube's English captions of a video spoken in another language: ones a person wrote if there are any,
    otherwise YouTube's own translation of its transcript. Word list like youtube_words, or None."""
    if not is_youtube(url):
        return None
    import json
    with _youtube_guard(url), _ydl({}, url) as ydl:
        i = ydl.extract_info(url, download=False)
        tracks = []
        for group in (i.get("subtitles") or {}, i.get("automatic_captions") or {}):
            for k in ("en", "en-US", "en-GB"):
                tracks.append(next((f for f in group.get(k) or [] if f.get("ext") == "json3" and f.get("url")), None))
        track = next((t for t in tracks if t), None)
        if not track:
            return None
        raw = ydl.urlopen(track["url"]).read(40_000_000)
    words = _caption_words(json.loads(raw))
    return words or None


def _caption_words(data: dict) -> list:
    out = []
    for ev in data.get("events") or []:
        segs = [x for x in ev.get("segs") or [] if (x.get("utf8") or "").strip()]
        if not segs:
            continue
        t0, dur = float(ev.get("tStartMs") or 0), float(ev.get("dDurationMs") or 0)
        timed = len(segs) > 1 or "tOffsetMs" in segs[0]
        for x in segs:
            parts = x["utf8"].split()
            for n, w in enumerate(parts):
                if re.fullmatch(r"[\[(].*[\])]", w) or w in ("[", "]", "__"):
                    continue                      # [Music], [Applause], and words YouTube blanked out
                # a line with no word timings: its words are spread evenly over the time the line was on screen
                at = t0 + float(x.get("tOffsetMs") or 0) if timed else t0 + dur * n / max(1, len(parts))
                out.append({"w": w, "s": round(at / 1000, 2)})
    out.sort(key=lambda w: w["s"])
    for n, w in enumerate(out):
        nxt = out[n + 1]["s"] if n + 1 < len(out) else w["s"] + 0.4
        w["e"] = round(max(w["s"] + 0.08, min(nxt, w["s"] + 0.6)), 2)
    return out


_PREVIEWS: dict = {}


def preview(url: str) -> dict:
    """What the user will get from a link, checked before any work starts. The thumbnail comes back inline
    (the page may only load images from this site). Cached, so retyping a link costs nothing."""
    url = url.strip()
    if url in _PREVIEWS:
        return _PREVIEWS[url]
    i = info(url)
    if (i["kind"] != "video" and not i.get("is_live")) or not i["title"]:
        raise ValueError("That link is a channel or playlist, not a single video.")
    thumb = ""
    t = i.get("thumbnail") or ""
    if t.startswith("https://"):
        import base64
        import urllib.request
        try:
            req = urllib.request.Request(t, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip()
                data = r.read(600_000 + 1)
            if ctype in ("image/jpeg", "image/png", "image/webp") and len(data) <= 600_000:
                thumb = f"data:{ctype};base64," + base64.b64encode(data).decode()
        except Exception:
            thumb = ""
    out = {"title": i["title"][:200], "uploader": i["uploader"][:120],
           "description": i.get("description") or "", "duration": i["duration"],
           "is_live": i["is_live"], "live_status": i.get("live_status", ""),
           "live_started_at": i.get("live_started_at"), "live_elapsed": i.get("live_elapsed", 0), "thumb": thumb}
    if len(_PREVIEWS) > 300:
        _PREVIEWS.pop(next(iter(_PREVIEWS)))
    _PREVIEWS[url] = out
    return out


def save_thumb(job_dir: Path, url: str = "", video: Path = None) -> bool:
    """A small picture for the video list: the link's own thumbnail, or a frame from an uploaded file."""
    import base64
    out = Path(job_dir) / "clips" / "thumb.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if url:
            p = _PREVIEWS.get(url.strip()) or preview(url)
            if not p.get("thumb"):
                return False
            out.write_bytes(base64.b64decode(p["thumb"].split(",", 1)[1]))
            return True
        if video:
            d = probe(video).get("duration") or 0
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(3.0, d / 3):.2f}", "-i", str(video),
                 "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", str(out)])
            return out.is_file()
    except Exception:
        return False
    return False


def download_audio(url: str, job_dir: Path, on_progress=None, cancel=None) -> Path:
    """Audio only: a few seconds even for long videos, and all the AI needs to pick clips."""
    def hook(d):
        if cancel is not None and cancel.is_set():
            raise RuntimeError("cancelled")
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if on_progress and d.get("status") == "downloading" and total:
            on_progress(d.get("downloaded_bytes", 0) / total)

    with _youtube_guard(url), _ydl({"format": "ba[ext=m4a]/ba/worst", "outtmpl": str(job_dir / "audio_src.%(ext)s"),
               "progress_hooks": [hook]}, url) as ydl:
        ydl.download([url])
    return _biggest(job_dir, "audio_src")


def download(url: str, job_dir: Path, height=720, cancel=None) -> Path:
    """The whole video. Used for shorter videos, where this is quicker than fetching pieces."""
    def hook(d):
        if cancel is not None and cancel.is_set():
            raise RuntimeError("cancelled")
    with _youtube_guard(url), _ydl({"format": _video_format(height), "merge_output_format": "mp4",
                                    "outtmpl": str(job_dir / "source.%(ext)s"), "progress_hooks": [hook]}, url) as ydl:
        ydl.download([url])
    return _biggest(job_dir, "source")


def _bounded_live_fragments(source, limit: int, cancel=None):
    """Return a yt-dlp fragment generator that ends after the elapsed live window."""
    def bounded(ctx):
        for index, fragment in enumerate(source(ctx)):
            if cancel is not None and cancel.is_set():
                raise RuntimeError("cancelled")
            if index >= limit:
                break
            yield fragment
    return bounded


def download_live_from_start(url: str, job_dir: Path, duration: float, height=720, cancel=None,
                             on_progress=None) -> Path:
    """Download the already-elapsed portion of a live YouTube stream.

    YouTube's live-from-start DASH formats expose DVR fragments beginning at the
    broadcast start.  The normal live downloader follows the edge forever, so we
    bound each selected format to the live duration measured during metadata
    lookup.  Ending the fragment generators cleanly lets yt-dlp finalize a
    playable MP4 instead of leaving an interrupted ``.part`` file.
    """
    if duration <= 0:
        raise RuntimeError("YouTube did not report how long this live stream has been running yet. Try again in a moment.")
    norm_url = normalize_url(url)
    out_dir = Path(job_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fragment_limit = None
    last_fraction = [-1.0]

    def hook(state):
        if cancel is not None and cancel.is_set():
            raise RuntimeError("cancelled")
        if not on_progress or state.get("status") not in ("downloading", "finished"):
            return
        index = state.get("fragment_index")
        if index is None or fragment_limit is None:
            return
        fraction = min(1.0, max(0.0, (int(index) + 1) / fragment_limit))
        if fraction > last_fraction[0]:
            last_fraction[0] = fraction
            on_progress(fraction)

    opts = {"format": _video_format(int(height or 720)), "merge_output_format": "mp4",
            "outtmpl": str(out_dir / "source.%(ext)s"), "live_from_start": True,
            "noprogress": True, "concurrent_fragment_downloads": 1,
            "progress_hooks": [hook]}
    try:
        with _youtube_guard(norm_url), _ydl(opts, norm_url) as ydl:
            try:
                info_data = ydl.extract_info(norm_url, download=False)
            except Exception:
                if norm_url != url:
                    with _youtube_guard(url), _ydl(opts, url) as ydl2:
                        info_data = ydl2.extract_info(url, download=False)
                else:
                    raise
            if not info_data or info_data.get("live_status") != "is_live":
                raise RuntimeError("That stream is no longer live. Refresh the link and try the saved video instead.")
            selected = info_data.get("requested_formats") or [info_data]
            durations = [float(f.get("target_duration") or 0) for f in selected if f.get("target_duration")]
            fragment_duration = min(durations or [2.0])
            fragment_limit = max(1, int(math.ceil(float(duration) / fragment_duration)) + 1)
            for selected_format in selected:
                source = selected_format.get("fragments")
                if not callable(source):
                    raise RuntimeError("YouTube did not expose DVR fragments from the start of this live stream.")
                selected_format["fragments"] = _bounded_live_fragments(source, fragment_limit, cancel)
            ydl.process_info(info_data)
    except Exception:
        if cancel is not None and cancel.is_set():
            for path in out_dir.glob("source.*"):
                path.unlink(missing_ok=True)
        raise
    if on_progress:
        on_progress(1.0)
    return _biggest(out_dir, "source")


def download_section(url: str, out_dir: Path, stem: str, start: float, end: float, height=720, cancel=None) -> Path:
    """Just one stretch of the video. The cut lands on a keyframe, so find_offset() pins the true start."""
    from yt_dlp.utils import download_range_func
    out_dir.mkdir(parents=True, exist_ok=True)
    def hook(d):
        if cancel is not None and cancel.is_set():
            raise RuntimeError("cancelled")
    with _youtube_guard(url), _ydl({"format": _video_format(height), "merge_output_format": "mp4",
               "outtmpl": str(out_dir / (stem + ".%(ext)s")),
               "download_ranges": download_range_func(None, [(max(0.0, start), end)]),
               "progress_hooks": [hook]}, url) as ydl:
        ydl.download([url])
    return _biggest(out_dir, stem)


def find_offset(full: np.ndarray, part: np.ndarray, expected: float, search=20.0) -> float:
    """Where in the full audio (seconds) a downloaded piece really begins, by matching the sound itself."""
    n = min(len(part), 30 * 16000)
    a0 = max(0, int((expected - search) * 16000))
    hay = full[a0: int((expected + search) * 16000) + n].astype(np.float32)
    needle = part[:n].astype(np.float32)
    if n < 16000 or len(hay) < n or float(np.abs(needle).mean()) < 20:
        return expected  # too short or silent to match: trust the requested time
    size = 1 << (len(hay) + n).bit_length()
    corr = np.fft.irfft(np.fft.rfft(hay, size) * np.conj(np.fft.rfft(needle, size)), size)[: len(hay) - n + 1]
    return (a0 + int(np.argmax(corr))) / 16000


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    data = json.loads(out)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if not v:
        raise RuntimeError("This file has no video track.")
    if not any(s["codec_type"] == "audio" for s in data["streams"]):
        raise RuntimeError("This file has no audio track, so there is nothing to transcribe.")
    w, h = int(v["width"]), int(v["height"])
    if w * h > 3840 * 2160 or w < 16 or h < 16:
        raise RuntimeError("This video's resolution isn't supported (4K is the largest).")
    rot = str((v.get("side_data_list") or [{}])[0].get("rotation", "0"))
    if rot.lstrip("-") in ("90", "270"):
        w, h = h, w
    return {"width": w, "height": h, "duration": float(data["format"]["duration"])}


def extract_audio(src: Path, wav: Path, cancel=None):
    # first_pts=0 pads any gap before the audio starts, so second 0 of the wav is second 0 of the file
    # -t: never more audio than the longest video allowed, whatever the file claims about itself
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-t", str(int(config.MAX_VIDEO_HOURS * 3600) + 60),
         "-af", "aresample=async=1:first_pts=0", "-c:a", "pcm_s16le", str(wav)], cancel=cancel)


def load_audio(wav: Path) -> np.ndarray:
    data, sr = sf.read(str(wav), dtype="int16")
    assert sr == 16000
    return data


def loudness_per_second(audio: np.ndarray) -> np.ndarray:
    """RMS level in dB for each second of audio."""
    n = len(audio) // 16000
    if n == 0:
        return np.zeros(1, dtype=np.float32)
    x = audio[: n * 16000].reshape(n, 16000).astype(np.float32) / 32768.0
    rms = np.sqrt((x ** 2).mean(axis=1) + 1e-10)
    return (20 * np.log10(rms)).astype(np.float32)


def resolve_stream(url: str) -> dict:
    """Resolve playable direct stream address for a live stream."""
    norm_url = normalize_url(url)
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
            "format": "b[height<=720]/bv*[height<=720]+ba/b"}
    with _youtube_guard(norm_url), _ydl(opts, norm_url) as ydl:
        try:
            info_data = ydl.extract_info(norm_url, download=False)
        except Exception:
            if norm_url != url:
                with _youtube_guard(url), _ydl(opts, url) as ydl2:
                    info_data = ydl2.extract_info(url, download=False)
            else:
                raise
    if not info_data:
        raise RuntimeError("Could not open that live stream.")
    fmts = info_data.get("requested_formats") or [info_data]
    urls = [f["url"] for f in fmts if f.get("url")]
    if not urls and info_data.get("url"):
        urls = [info_data["url"]]
    title = info_data.get("title") or ""
    if "(live)" in title and info_data.get("description"):
        title = str(info_data["description"]).splitlines()[0][:120]
    return {
        "urls": urls,
        "title": title,
        "uploader": info_data.get("uploader") or info_data.get("channel") or "",
        "is_live": bool(info_data.get("is_live") or info_data.get("live_status") == "is_live")
    }


def capture_live(url: str, out_path: Path, duration: float = 600.0, cancel=None, on_progress=None) -> Path:
    """Capture up to `duration` seconds of the latest live content from a live stream."""
    st = resolve_stream(url)
    urls = st.get("urls") or []
    if not urls:
        raise RuntimeError("Could not find a playable stream address for this live stream.")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
    ]
    for u in urls:
        cmd += ["-i", u]
    if len(urls) > 1:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0?", "-map", "0:a:0?"]
    cmd += [
        "-t", str(int(duration)),
        "-c:v", "copy",
        "-c:a", "aac",
        "-bsf:a", "aac_adtstoasc",
        "-movflags", "+faststart",
        str(out_path)
    ]
    def report(elapsed):
        if on_progress:
            on_progress(min(1.0, max(0.0, elapsed / max(1.0, duration))))
    try:
        run(cmd, timeout=int(duration) + 120, cancel=cancel, on_progress=report)
    except Exception:
        cmd_fallback = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        ]
        for u in urls:
            cmd_fallback += ["-i", u]
        if len(urls) > 1:
            cmd_fallback += ["-map", "0:v:0", "-map", "1:a:0"]
        else:
            cmd_fallback += ["-map", "0:v:0?", "-map", "0:a:0?"]
        cmd_fallback += [
            "-t", str(int(duration)),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(out_path)
        ]
        run(cmd_fallback, timeout=int(duration) + 180, cancel=cancel, on_progress=report)

    if not out_path.is_file() or out_path.stat().st_size < 1000:
        raise RuntimeError("Live stream capture did not produce playable video.")
    return out_path
