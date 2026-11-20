"""Job pipeline: get video -> audio -> transcript -> AI picks -> rendered clips. One heavy task at a time."""
import collections
import json
import os
import math
import queue
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from . import brain, config, creators, ctx, load, media, render, roman, safe, transcribe, usage

class _FairQueue:
    """Whose video is next. Each person has their own line and the lines take turns, so someone who adds ten
    videos does not make everyone else wait behind all ten. Small tasks (re-making one clip) go first."""

    def __init__(self):
        self.cv = threading.Condition()
        self.quick = collections.deque()
        self.lines = {}                       # user -> their waiting videos, oldest first
        self.turn = collections.deque()       # users with something waiting, in the order they will be served
        self.epoch = 0                        # goes up whenever the line moves
        self._pos = (0.0, {})
        self.running = 0                      # videos being worked on right now
        self.last_start = 0.0
        self.held = False                     # videos are waiting only because the machine is near full

    def _room(self) -> bool:
        """May one more video start? One always may. More only while the machine has room, and a few seconds
        after the last one started, so its weight is already showing in the measurements."""
        if self.running == 0:
            return True
        return self.running < config.JOB_WORKERS and time.time() - self.last_start > 6 and not load.busy()

    def done(self):
        with self.cv:
            self.running = max(0, self.running - 1)
            self.cv.notify_all()

    def put(self, item, user=None):
        with self.cv:
            if user is None:
                self.quick.append(item)
            else:
                if user not in self.lines:
                    self.lines[user] = collections.deque()
                    self.turn.append(user)
                self.lines[user].append(item)
            self.epoch += 1
            self.cv.notify()

    def get(self, quick_only=False):
        with self.cv:
            while True:
                if self.quick:
                    self.epoch += 1
                    return self.quick.popleft()
                if not quick_only and self.turn:
                    if self._room():
                        break
                    if not self.held:
                        self.held = True
                        self.epoch += 1
                elif self.held:
                    self.held = False
                    self.epoch += 1
                self.cv.wait(1.0)             # looked at again every second: the line moves the moment there is room
            self.epoch += 1
            self.held = False
            self.running += 1
            self.last_start = time.time()
            user = self.turn.popleft()
            item = self.lines[user].popleft()
            if self.lines[user]:
                self.turn.append(user)
            else:
                del self.lines[user]
            return item

    def ahead(self) -> dict:
        """job id -> how many videos will start before it. Worked out at most once a second."""
        with self.cv:
            if time.time() - self._pos[0] < 1:
                return self._pos[1]
            out, lines, order, n = {}, {u: list(q) for u, q in self.lines.items()}, list(self.turn), 0
            depth = 0
            while order:
                nxt = []
                for u in order:
                    if depth < len(lines[u]):
                        out[lines[u][depth][1]] = n
                        n += 1
                        if depth + 1 < len(lines[u]):
                            nxt.append(u)
                order, depth = nxt, depth + 1
            self._pos = (time.time(), out)
            return out


_q = _FairQueue()
_live_q: "queue.Queue" = queue.Queue()   # live clips never wait behind a long video
_jobs: dict = {}
_by_user: dict = {}                       # user -> {job id: job}: listing one person's videos never scans everyone's
_lock = threading.RLock()
_cancel_events: dict = {}                 # full video generation -> Event
_more_cancel_events: dict = {}            # "find more" task -> Event
on_clip_ready: list = []   # callbacks (job, clip), run once when a clip first finishes

EFFECT_KEYS = ("captions", "emoji", "speech_cleanup", "audio_enhance", "auto_sfx", "color_correct", "auto_zoom",
               "auto_transition")
SPEECH_LANGUAGES = {"auto": "Auto-detect", "en": "English", "hi": "Hindi", "ur": "Urdu", "es": "Spanish",
                    "ar": "Arabic", "fr": "French", "de": "German", "pt": "Portuguese", "tr": "Turkish",
                    "id": "Indonesian", "it": "Italian", "ja": "Japanese", "ko": "Korean", "zh": "Chinese",
                    "ru": "Russian", "nl": "Dutch", "pl": "Polish", "sv": "Swedish", "vi": "Vietnamese",
                    "th": "Thai", "fa": "Persian", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
                    "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi", "sw": "Swahili", "other": "Other"}
GENRES = {"auto": "Auto-detect", "gaming": "Gaming", "reaction": "Reaction", "podcast": "Podcast",
          "interview": "Interview", "comedy": "Comedy", "story": "Storytelling", "commentary": "Commentary",
          "education": "Education", "vlog": "Vlog", "music": "Music", "other": "Other"}
ASPECTS = {"vertical": "9:16", "landscape": "16:9", "square": "1:1", "portrait": "4:5"}
EMOJI_PRESETS = {"subtle": "Subtle", "balanced": "Balanced", "expressive": "Expressive", "gaming": "Gaming reactions"}
CLEANUP_LEVELS = {"basic": "Basic noise reduction", "strong": "Stronger noise reduction"}
ZOOM_PRESETS = {"off": "Off", "gentle": "Gentle zoom", "punch": "Punch zoom", "cinematic": "Slow cinematic zoom"}
COLOR_PRESETS = {"original": "Original", "natural": "Natural", "vibrant": "Vibrant", "warm": "Warm", "cool": "Cool"}
TRANSITIONS = {"none": "None", "fade": "Fade", "dip_black": "Dip to black", "flash": "White flash"}
DEFAULTS = {"max_clips": 6, "min_len": 15, "max_len": 60, "style": "bounce", "layout": "blur", "quality": 720,
            "range_start": None, "range_end": None, "captions": True, "emoji": False, "speech_cleanup": False,
            "audio_enhance": False, "auto_sfx": False, "color_correct": False, "auto_zoom": False,
            "auto_transition": False, "moment_prompt": "", "speech_language": "auto", "caption_language": "auto", "genre": "auto",
            "aspect": "vertical", "emoji_preset": "balanced", "emoji_frequency": 3, "cleanup_level": "basic",
            "zoom_preset": "gentle", "color_preset": "original", "color_brightness": 0,
            "color_contrast": 100, "color_saturation": 100, "color_sharpness": 0, "transition": "fade"}


LIMITS = {"max_clips": (1, 12), "min_len": (5, 120), "max_len": (10, 180), "quality": (360, 1080),
          "emoji_frequency": (1, 5), "color_brightness": (-10, 10), "color_contrast": (80, 130),
          "color_saturation": (80, 130), "color_sharpness": (0, 100)}


def _bool(v):
    return v.lower() in ("1", "true", "yes", "on") if isinstance(v, str) else bool(v)


def clean_options(options) -> dict:
    """Only known settings, each inside its allowed range. Raises ValueError on nonsense."""
    out = {}
    for k, v in (options if isinstance(options, dict) else {}).items():
        if k not in DEFAULTS or v in ("", None):
            continue
        if k in LIMITS:
            lo, hi = LIMITS[k]
            v = max(lo, min(hi, int(float(v))))
        elif k == "style":
            v = v if v in render.STYLES else DEFAULTS["style"]
        elif k == "layout":
            v = v if v in render.LAYOUTS else DEFAULTS["layout"]
        elif k in EFFECT_KEYS:
            v = _bool(v)
        elif k == "moment_prompt":
            v = str(v).strip()[:500]
        elif k in ("speech_language", "caption_language"):
            v = str(v).strip().lower()
            if v not in SPEECH_LANGUAGES:
                raise ValueError("Choose a supported caption language.")
        elif k == "genre":
            v = str(v).strip().lower()
            if v not in GENRES:
                raise ValueError("Choose a supported video genre.")
        elif k == "aspect":
            v = str(v).strip().lower()
            if v not in ASPECTS:
                raise ValueError("Choose a supported aspect ratio.")
        elif k == "emoji_preset":
            v = str(v).strip().lower()
            if v not in EMOJI_PRESETS:
                raise ValueError("Choose a supported emoji preset.")
        elif k == "cleanup_level":
            v = str(v).strip().lower()
            if v not in CLEANUP_LEVELS:
                raise ValueError("Choose a supported speech-cleanup level.")
        elif k == "zoom_preset":
            v = str(v).strip().lower()
            if v not in ZOOM_PRESETS:
                raise ValueError("Choose a supported zoom preset.")
        elif k == "color_preset":
            v = str(v).strip().lower()
            if v not in COLOR_PRESETS:
                raise ValueError("Choose a supported color preset.")
        elif k == "transition":
            v = str(v).strip().lower()
            if v not in TRANSITIONS:
                raise ValueError("Choose a supported transition.")
        else:                                    # range_start, range_end: seconds into the video
            v = float(v)
            if not math.isfinite(v) or v < 0:
                raise ValueError("That part of the video isn't valid.")
        out[k] = v
    if out.get("range_end") is not None and out["range_end"] <= out.get("range_start", 0):
        raise ValueError("The end of the chosen part must be after its start.")
    return out


def job_dir(jid) -> Path:
    return Path(_jobs[jid]["dir"])


HIDDEN = ("dir", "user", "source_path", "recover")


def _event_for(events, jid):
    with _lock:
        return events.setdefault(jid, threading.Event())


def _cancelled(job, more=False):
    return (_event_for(_more_cancel_events if more else _cancel_events, job["id"]).is_set()
            or (not more and job.get("status") in ("cancelling", "cancelled")))


def _mark_pending_cancelled(job):
    changed = False
    for c in job.get("clips", []):
        if c.get("status") in ("queued", "rendering"):
            c.update(status="cancelled", error=None)
            changed = True
    if changed:
        save(job)


def public(job) -> dict:
    """What the browser may see: no server paths, no owner id."""
    out = {k: v for k, v in job.items() if k not in HIDDEN}
    out["source"] = {k: v for k, v in job["source"].items() if k != "path"}
    out["clips"] = [{k: v for k, v in c.items() if k not in ("src", "fixed_words", "fixed_for")} for c in job["clips"]]
    ai = job.get("ai") or {}
    selection = ai.get("selection") if isinstance(ai.get("selection"), dict) else {}
    out["ai"] = {"tokens": ai.get("tokens", 0), "note": ai.get("note", ""), "used": bool(ai.get("model")),
                 "selection": {k: selection[k] for k in ("candidates", "ranked", "accepted", "fallback", "fallback_windows",
                                                             "duration_ms", "target_seconds") if k in selection}}
    if job.get("status") == "queued":
        n = _q.ahead().get(job["id"])
        if n:
            out["stage"] = (f"High demand right now: {n} video{'s' if n != 1 else ''} ahead of yours" if _q.held else
                            f"Waiting in line: {n} video{'s' if n != 1 else ''} ahead of yours")
        elif n == 0 and _q.held:
            out["stage"] = "High demand right now: yours is next"
    return out


def save(job):
    ctx.bump(job.get("user"))
    with _lock:
        d = Path(job["dir"])
        for _ in range(5):
            try:
                text = json.dumps(job, indent=1)
                break
            except RuntimeError:  # changed mid-dump by another thread
                time.sleep(0.05)
        else:
            return
        tmp = d / "job.json.tmp"
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(d / "job.json")


def _set(job, **kw):
    with _lock:
        job.update(kw)
    save(job)


def _remap(path, folder: Path):
    """Paths saved before data moved into per-user folders (or on another machine): find the file by name."""
    if path and not Path(path).exists():
        cand = folder / Path(str(path).replace("\\", "/")).name
        if cand.exists():
            return str(cand)
    return path


def _load_file(f: Path, uid: str):
    try:
        job = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    job.update(dir=str(f.parent), user=uid)
    job.setdefault("kind", "video")
    job.setdefault("creator", None)
    job.setdefault("more", {"status": "idle", "progress": 0.0, "added": 0, "error": None})
    _event_for(_cancel_events, job["id"])
    _event_for(_more_cancel_events, job["id"])
    if job.get("source_path"):
        job["source_path"] = _remap(job["source_path"], f.parent)
    if job.get("source", {}).get("path"):
        job["source"]["path"] = _remap(job["source"]["path"], f.parent)
    if job.get("status") in ("queued", "running", "cancelling") and job.get("kind") != "live":
        # Picked up again as soon as the server is back (jobs.start), from the last finished part of the transcript.
        if job.get("status") == "cancelling":
            job.update(status="cancelled", stage="Cancelled by you", error=None)
        else:
            job.update(status="queued", stage="Picking up where it stopped", error=None, resume=True)
    if job.get("status") == "live":
        job.update(status="done", stage="Recording paused by a server update", was_live=True)
    buffered = job.get("kind") == "live" and any((f.parent / "buffer").glob("*.ts"))
    for c in job.get("clips", []):
        if c.get("src"):
            c["src"] = _remap(c["src"], f.parent / "clips")
        if c.get("status") in ("rendering", "queued"):
            if buffered and not c.get("src"):
                c["status"] = "queued"  # the stream is still on disk: live.recover() finishes these
                job["recover"] = True
            elif job.get("resume"):
                c["status"] = "queued"  # the video is being picked up again: this clip is made then
            elif job.get("kind") != "live" and (f.parent / "words.json").is_file():
                c["status"] = "queued"  # a single clip being re-made: jobs.start() makes it again
                job.setdefault("remake", []).append(c["id"])
            else:
                c.update(status="error", error="Interrupted by a restart. Open it and press Save and re-make.")
    _jobs[job["id"]] = job
    _by_user.setdefault(uid, {})[job["id"]] = job


def load_user(uid: str):
    d = config.USERS_DIR / uid
    for f in list((d / "jobs").glob("*/job.json")) + list((d / "creators").glob("*/*/*/job.json")):
        _load_file(f, uid)


def load_all():
    for d in config.USERS_DIR.iterdir():
        if d.is_dir():
            load_user(d.name)


def all_jobs() -> list:
    """Every user's jobs. Only for background work; never send this to a browser."""
    with _lock:
        return list(_jobs.values())


def list_jobs():
    u = ctx.uid()
    with _lock:
        return sorted((dict(j) for j in _by_user.get(u, {}).values()), key=lambda j: -j["created"])


def get(jid):
    """The job, only if it belongs to whoever this code is running for."""
    job = _jobs.get(jid)
    return job if job and job["user"] == ctx.uid() else None


def busy_count() -> int:
    u = ctx.uid()
    return sum(1 for j in list(_by_user.get(u, {}).values()) if j["kind"] == "video" and j["status"] in ("queued", "running", "cancelling"))


def waiting_total() -> int:
    return sum(1 for j in list(_jobs.values()) if j["kind"] == "video" and j["status"] == "queued")


def queue_epoch() -> int:
    return _q.epoch


def running_now() -> int:
    return _q.running


def create(source: dict, options: dict, enqueue=True, creator=None, kind="video") -> dict:
    jid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:10]
    c = creators.get(creator) if creator else None
    if c:
        d = creators.root(c["id"]) / ("live" if kind == "live" else "videos") / jid
        base = {**DEFAULTS, **{k: c[k] for k in ("max_clips", "min_len", "max_len", "style", "layout")}}
    else:
        d, base, creator = config.user_dir(ctx.uid()) / "jobs" / jid, dict(DEFAULTS), None
    d.mkdir(parents=True)
    opts = {**base, **clean_options(options)}
    if opts["min_len"] >= opts["max_len"]:
        opts["min_len"] = max(5, opts["max_len"] - 5)
    job = {"id": jid, "user": ctx.uid(), "kind": kind, "creator": creator, "dir": str(d), "created": time.time(), "source": source,
           "options": opts, "status": "queued", "stage": "Waiting", "progress": 0.0,
           "title": source.get("name", ""), "uploader": "", "duration": 0, "clips": [], "error": None, "ai": {},
           "more": {"status": "idle", "progress": 0.0, "added": 0, "error": None}}
    with _lock:
        _jobs[jid] = job
        _by_user.setdefault(job["user"], {})[jid] = job
        _cancel_events[jid] = threading.Event()
        _more_cancel_events[jid] = threading.Event()
    save(job)
    if enqueue:
        _q.put(("job", jid, None), user=job["user"])
    return job


def enqueue(job):
    save(job)
    _q.put(("job", job["id"], None), user=job["user"])


def submit(fn):
    """Run any heavy task (a render, a cleanup) on the single worker, in order."""
    _q.put(("fn", ctx.bind(fn), None))


def submit_live(fn):
    """Live-stream renders and cleanups: their own worker, so a long video can never hold them up."""
    _live_q.put(ctx.bind(fn))


def _live_worker():
    while True:
        fn = _live_q.get()
        try:
            fn()
        except Exception:  # noqa: BLE001
            traceback.print_exc()


def delete(jid):
    with _lock:
        job = _jobs.pop(jid, None)
        if job:
            _by_user.get(job["user"], {}).pop(jid, None)
            _cancel_events.pop(jid, None)
            _more_cancel_events.pop(jid, None)
    if job:
        ctx.bump(job["user"])
        shutil.rmtree(job["dir"], ignore_errors=True)
    return bool(job)


def cancel_job(jid):
    job = _jobs[jid]
    if job.get("status") not in ("queued", "running", "cancelling"):
        raise ValueError("This video is not being generated now.")
    _event_for(_cancel_events, jid).set()
    if job.get("status") == "queued":
        _set(job, status="cancelled", stage="Cancelled by you", error=None)
        _mark_pending_cancelled(job)
    elif job.get("status") == "running":
        _set(job, status="cancelling", stage="Stopping…", error=None)
    return job


def cancel_more(jid):
    job = _jobs[jid]
    more = job.setdefault("more", {"status": "idle", "progress": 0.0, "added": 0, "error": None})
    if more.get("status") not in ("queued", "running", "cancelling"):
        raise ValueError("There is no extra clip search running.")
    _event_for(_more_cancel_events, jid).set()
    if more.get("status") in ("queued", "running"):
        more.update(status="cancelling", note="Stopping…")
        save(job)
    return job


def _next_clip_id(job):
    used = {c.get("id") for c in job.get("clips", [])}
    n = 1
    while f"clip{n:02d}" in used:
        n += 1
    return f"clip{n:02d}"


def request_cut(jid, changes: dict):
    """Queue a hand-selected clip without replacing any existing clip."""
    job = _jobs[jid]
    if job.get("status") != "done":
        raise ValueError("Wait until the original video has finished first.")
    try:
        start, end = float(changes.get("start")), float(changes.get("end"))
    except (TypeError, ValueError):
        raise ValueError("Those times aren't valid.")
    duration = float(job.get("duration") or 0)
    if not (math.isfinite(start) and math.isfinite(end)) or start < 0 or end <= start:
        raise ValueError("Those times aren't valid.")
    if duration and end > duration + 0.05:
        raise ValueError("The end time is past the original video's duration.")
    if not 3 <= end - start <= 180:
        raise ValueError("A clip can be 3 to 180 seconds long.")
    o = {**DEFAULTS, **(job.get("options") or {})}
    cid = _next_clip_id(job)
    clip = {"id": cid, "start": round(start, 2), "end": round(end, 2), "score": 0,
            "category": "hand", "hook": str(changes.get("hook") or "Highlight")[:60],
            "title": str(changes.get("title") or "")[:100],
            "description": str(changes.get("description") or "")[:2000],
            "hashtags": [], "highlight_words": [], "reason": "Cut from the original video by hand.",
            "style": changes.get("style") if changes.get("style") in render.STYLES else o.get("style", DEFAULTS["style"]),
            "layout": changes.get("layout") if changes.get("layout") in render.LAYOUTS else o.get("layout", DEFAULTS["layout"]),
            "aspect": o.get("aspect", DEFAULTS["aspect"]), "emoji_preset": o.get("emoji_preset", DEFAULTS["emoji_preset"]),
            "emoji_frequency": o.get("emoji_frequency", DEFAULTS["emoji_frequency"]),
            "cleanup_level": o.get("cleanup_level", DEFAULTS["cleanup_level"]),
            "zoom_preset": o.get("zoom_preset", DEFAULTS["zoom_preset"]),
            "color_preset": o.get("color_preset", DEFAULTS["color_preset"]),
            "color_brightness": o.get("color_brightness", DEFAULTS["color_brightness"]),
            "color_contrast": o.get("color_contrast", DEFAULTS["color_contrast"]),
            "color_saturation": o.get("color_saturation", DEFAULTS["color_saturation"]),
            "transition": o.get("transition", DEFAULTS["transition"]),
            **{k: _bool(changes.get(k, o.get(k, DEFAULTS[k]))) for k in EFFECT_KEYS},
            "status": "queued", "version": 0}
    job["clips"].append(clip)
    save(job)
    _q.put(("clip", jid, cid))
    return job


def request_more(jid):
    job = _jobs[jid]
    if job.get("status") != "done":
        raise ValueError("Wait until the original video has finished first.")
    if not (Path(job["dir"]) / "words.json").is_file():
        raise ValueError("The original transcript is not available for another search.")
    more = job.setdefault("more", {"status": "idle", "progress": 0.0, "added": 0, "error": None})
    if more.get("status") in ("queued", "running", "cancelling"):
        raise ValueError("Another clip search is already running.")
    ev = _event_for(_more_cancel_events, jid)
    ev.clear()
    more.update(status="queued", progress=0.0, added=0, error=None, note="Looking for moments not already used…")
    save(job)
    submit(lambda: _run_more(job))
    return job


def request_render(jid, cid, changes: dict):
    job = _jobs[jid]
    if job.get("status") != "done":
        raise ValueError("Wait until the video has finished before editing a clip.")
    clip = next(c for c in job["clips"] if c["id"] == cid)
    new = dict(clip)
    for k in ("start", "end"):
        if k in changes:
            new[k] = round(float(changes[k]), 2)
    if "src_offset" in clip:  # live clip: can only move inside the saved piece of stream
        new["start"] = max(new["start"], clip["src_offset"])
        new["end"] = min(new["end"], clip["src_end"])
    if not (math.isfinite(new["start"]) and math.isfinite(new["end"])) or new["start"] < 0:
        raise ValueError("Those times aren't valid.")
    if not 3 <= new["end"] - new["start"] <= 180:
        raise ValueError("A clip can be 3 to 180 seconds long.")
    for k in ("hook", "title", "description", "style", "layout", "aspect", "emoji_preset", "emoji_frequency",
              "cleanup_level", "zoom_preset", "color_preset", "color_brightness", "color_contrast",
              "color_saturation", "color_sharpness", "transition") + EFFECT_KEYS:
        if k in changes:
            if k in EFFECT_KEYS:
                new[k] = _bool(changes[k])
            elif k in ("emoji_frequency", "color_brightness", "color_contrast", "color_saturation", "color_sharpness"):
                lo, hi = LIMITS[k]
                new[k] = max(lo, min(hi, int(float(changes[k]))))
            else:
                new[k] = str(changes[k])[:{"hook": 60, "title": 100, "description": 2000}.get(k, 40)]
    if new.get("style") not in render.STYLES:
        new["style"] = DEFAULTS["style"]
    if new.get("layout") not in render.LAYOUTS:
        new["layout"] = DEFAULTS["layout"]
    if new.get("aspect") not in ASPECTS:
        new["aspect"] = DEFAULTS["aspect"]
    if new.get("emoji_preset") not in EMOJI_PRESETS:
        new["emoji_preset"] = DEFAULTS["emoji_preset"]
    if new.get("cleanup_level") not in CLEANUP_LEVELS:
        new["cleanup_level"] = DEFAULTS["cleanup_level"]
    if new.get("zoom_preset") not in ZOOM_PRESETS:
        new["zoom_preset"] = DEFAULTS["zoom_preset"]
    if new.get("color_preset") not in COLOR_PRESETS:
        new["color_preset"] = DEFAULTS["color_preset"]
    if new.get("transition") not in TRANSITIONS:
        new["transition"] = DEFAULTS["transition"]
    clip.update(new, status="queued")
    save(job)
    _q.put(("clip", jid, cid))


def render_one(job, clip, words):
    d = Path(job["dir"])
    cancel = _event_for(_more_cancel_events if clip.get("more_run") else _cancel_events, job["id"])
    if cancel.is_set() or job.get("status") in ("cancelling", "cancelled"):
        clip.update(status="cancelled", error=None)
        save(job)
        return
    clip["status"] = "rendering"
    save(job)
    try:
        off = clip.get("src_offset", 0.0)
        if not clip.get("src") and not job.get("source_path") and job.get("source", {}).get("type") == "url":
            _fetch_piece(job, clip, None, cancel)
        if cancel.is_set():
            clip.update(status="cancelled", error=None)
            save(job)
            return
        if clip.get("src"):
            src = Path(clip["src"])
        elif job.get("source_path"):
            src = Path(job["source_path"])
        else:
            raise RuntimeError("The original video file is not available for this clip.")
        if clip.get("src_offset") is not None:
            off = clip.get("src_offset", 0.0)
        if not clip.get("src"):
            clip["end"] = min(clip["end"], job["duration"])
        local = dict(clip, start=clip["start"] - off, end=clip["end"] - off, hook=roman.to_roman(clip.get("hook") or ""))
        caption_language = (job.get("caption_language") or (job.get("options") or {}).get("caption_language") or "auto")
        span = [round(clip["start"], 2), round(clip["end"], 2), caption_language]
        if clip.get("fixed_for") == span and clip.get("fixed_words"):
            raw = clip["fixed_words"]          # already tidied for this exact span: no second AI call
        else:
            raw = [w for w in words if clip["start"] - 1 <= w["s"] <= clip["end"] + 1]
            try:
                usage.set_context(job.get("creator"), job.get("title") or "")
                raw = brain.caption_words(raw, job.get("lang") or "", caption_language, job.get("title") or "",
                                          youtube_english=lambda: _english_part(job, clip))
                clip.update(fixed_words=raw, fixed_for=span)
            except Exception:  # noqa: BLE001 - captions still render with the words as heard
                pass
        # ``caption_words`` already returns the requested display language. Do not Romanise it here: that would
        # destroy an explicitly selected Urdu, Hindi, Arabic, or other native-script caption language.
        near = [dict(w, s=w["s"] - off, e=w["e"] - off) for w in raw]
        out = render.render_clip(src, d / "clips", clip["id"], local, near, job["width"], job["height"], cancel,
                                 output_aspect=clip.get("aspect", DEFAULTS["aspect"]))
        if cancel.is_set():
            clip.update(status="cancelled", error=None)
            save(job)
            return
        clip.update(out, status="done", version=clip.get("version", 0) + 1, error=None)
        post = {k: clip[k] for k in ("title", "description", "hashtags", "hook", "start", "end", "score")}
        (d / "clips" / f"{clip['id']}.json").write_text(json.dumps(post, indent=1), encoding="utf-8")
        if clip["version"] == 1:
            clip.setdefault("made_at", time.time())
            creators.log(job["creator"], f"Clip ready (score {clip['score']}): {clip['title'] or clip['hook']}")
            save(job)
            for fn in on_clip_ready:
                try:
                    fn(job, clip)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
    except Exception as e:  # noqa: BLE001
        if cancel.is_set() or str(e).lower() == "cancelled":
            clip.update(status="cancelled", error=None)
        else:
            clip.update(status="error", error=safe.friendly(e, 400))
            creators.log(job["creator"], f"Clip failed: {safe.friendly(e, 200)}")
    save(job)


CLIP_MINUTES = float(config.env("PEAKCUT_CLIP_MINUTES", "15"))     # the longest one clip may take to make


def _wait_for_clips(job, futures, began, workers):
    """Wait for a video's clips, but not for ever. A clip that hangs (a download that stalls, an encoder that
    freezes) used to keep the whole video "in progress", and no other clip could be re-made. Now it is marked as
    failed after CLIP_MINUTES and the video finishes with the clips that did work."""
    left, given_up = list(futures), 0
    late = "This clip took too long and was stopped. Open it and press Save and re-make to try again."
    while left:
        still = []
        for f, clip in left:
            if f.done():
                if not f.cancelled():
                    f.result()
                continue
            if _cancelled(job):
                f.cancel()
                if clip.get("status") in ("queued", "rendering"):
                    clip.update(status="cancelled", error=None)
                    save(job)
                continue
            t = began.get(clip["id"])
            if (t and time.time() - t > CLIP_MINUTES * 60) or (not t and given_up >= workers):
                given_up += 1
                clip.update(status="error", error=late)
                creators.log(job["creator"], f"Clip stopped after {CLIP_MINUTES:g} minutes: {clip.get('title') or clip.get('hook') or clip['id']}")
                save(job)
                continue
            still.append((f, clip))
        left = still
        if left:
            time.sleep(1)


def _english_part(job, clip):
    """YouTube's English captions for just this clip, for a video in another language. Fetched once per video."""
    if (job.get("source") or {}).get("type") != "url":
        return None
    f = Path(job["dir"]) / "words_en.json"
    if f.is_file():
        en = json.loads(f.read_text(encoding="utf-8"))
    else:
        try:
            en = media.youtube_english_words(job["source"]["url"]) or []
        except Exception:  # noqa: BLE001 - YouTube often refuses its translations: the AI translates instead
            en = []
        f.write_text(json.dumps(en), encoding="utf-8")       # asked once per video, refused or not
    return [w for w in en if clip["start"] - 0.5 <= w["s"] <= clip["end"] + 0.5]


LONG_VIDEO = 40 * 60   # above this, fetch only the pieces that become clips
PAD = 8                # seconds kept either side of a fetched piece, so clips can be re-trimmed


def _fetch_piece(job, clip, full_audio=None, cancel=None):
    """Long videos: download just this clip's stretch and pin down exactly where it starts."""
    d = Path(job["dir"])
    o = {**DEFAULTS, **(job.get("options") or {})}
    try:
        want = max(0.0, clip["start"] - PAD)
        piece = media.download_section(job["source"]["url"], d / "clips", f"{clip['id']}.src", want,
                                       min(job["duration"], clip["end"] + PAD), int(o["quality"]), cancel)
        wav = d / "clips" / f"{clip['id']}.wav"
        media.extract_audio(piece, wav, cancel)
        if cancel is not None and cancel.is_set():
            raise RuntimeError("cancelled")
        part = media.load_audio(wav)
        wav.unlink(missing_ok=True)
        meta = media.probe(piece)
        off = media.find_offset(full_audio, part, want) if full_audio is not None else want
        clip.update(src=str(piece), src_offset=round(off, 2), src_end=round(off + meta["duration"], 2))
        clip["start"], clip["end"] = max(clip["start"], clip["src_offset"]), min(clip["end"], clip["src_end"])
        job.setdefault("width", meta["width"])
        job.setdefault("height", meta["height"])
    except Exception as e:  # noqa: BLE001
        if cancel is not None and cancel.is_set():
            clip.update(status="cancelled", error=None)
        else:
            clip.update(status="error", error=f"Could not fetch this part of the video: {safe.friendly(e, 250)}")


BLOCK = 10 * 60         # long videos are transcribed and clipped one block at a time
PROGRESSIVE_FROM = 20 * 60


def _time_label(seconds):
    """Short elapsed-time label for live-history progress messages."""
    total = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _covers(words: list, start: float, end: float) -> bool:
    """Is a borrowed transcript good enough to find clips with? It has to reach the end of the part being clipped
    and have a normal amount of talking in it; otherwise our own model writes the transcript."""
    inside = [w for w in words if start <= w["s"] <= end]
    minutes = max(0.5, (end - start) / 60)
    return len(inside) >= 25 * minutes and inside[-1]["s"] >= start + 0.85 * (end - start)


def _run_job(job):
    import math
    from concurrent.futures import ThreadPoolExecutor
    d = Path(job["dir"])
    o = job["options"]
    # Keep the source-language hint and the display-language choice separate. Older jobs only have
    # speech_language, so the fallback keeps those jobs renderable without changing their saved data.
    job["caption_language"] = o.get("caption_language") or o.get("speech_language") or "auto"
    src = job["source"]
    t0 = time.time()
    cancel = _event_for(_cancel_events, job["id"])
    if cancel.is_set() or job.get("status") == "cancelled":
        _mark_pending_cancelled(job)
        _set(job, status="cancelled", stage="Cancelled by you", error=None)
        return
    notes = []
    usage.set_context(job["creator"], job["title"] or src.get("name"))
    resuming = bool(job.pop("resume", False)) and (d / "words.json").is_file()
    if resuming:   # after a restart: keep the transcript parts, clips and AI answers already made, and carry on
        _set(job, status="running", stage="Picking up where it stopped", error=None)
    else:
        _set(job, status="running", stage="Getting the audio", progress=0.03, error=None, clips=[], ai={}, done_blocks=0)
    if not transcribe.model_ready() and not transcribe.REMOTE:
        from . import fetch_model
        _set(job, stage="Getting the speech model (one time, about 480 MB)")
        fetch_model.ensure()
        _set(job, stage="Getting the audio")
    fetch = ThreadPoolExecutor(1)
    video = None
    if src["type"] == "url":
        meta = media.info(src["url"])
        if meta["kind"] != "video" and not meta.get("is_live"):
            raise RuntimeError("That link is a channel or playlist, not a single video. Paste the link of one video.")
        if meta.get("is_live") and (meta.get("live_status") or "is_live") == "is_live":
            live_elapsed = float(meta.get("live_elapsed") or 0)
            if live_elapsed <= 0:
                raise RuntimeError("YouTube did not report the live start time yet. Refresh the link and try again.")
            if live_elapsed > config.MAX_VIDEO_HOURS * 3600:
                raise RuntimeError(f"This live stream has been running for {_time_label(live_elapsed)}, which is over the {config.MAX_VIDEO_HOURS:g}-hour processing limit.")
            _set(job, title=meta["title"], uploader=meta["uploader"], is_live=True, live_status="is_live",
                 live_started_at=meta.get("live_started_at"), live_elapsed=round(live_elapsed), views=meta.get("views"))
            if not job.get("thumb") and media.save_thumb(d, url=src["url"]):
                _set(job, thumb=True)
            usage.set_context(job["creator"], meta["title"])
            _set(job, stage=f"Scanning live history · 0:00 / {_time_label(live_elapsed)}", progress=0.08)
            source_file = d / "source.mp4"
            def live_progress(fraction):
                elapsed = min(live_elapsed, max(0, round(live_elapsed * fraction)))
                _set(job, stage=f"Scanning live history · {_time_label(elapsed)} / {_time_label(live_elapsed)}",
                     progress=0.08 + 0.13 * fraction)
            media.download_live_from_start(src["url"], d, live_elapsed, int(o.get("quality") or DEFAULTS["quality"]), cancel, live_progress)
            pinfo = media.probe(source_file)
            _set(job, source_path=str(source_file), width=pinfo["width"], height=pinfo["height"],
                 duration=pinfo["duration"], live_scanned=round(pinfo["duration"], 2), progress=0.22)
            pieces = False
            video = None
            audio_file = d / "live_audio.wav"
            media.extract_audio(source_file, audio_file, cancel)
        else:
            if ((o["range_end"] or meta["duration"]) - (o["range_start"] or 0)) > config.MAX_VIDEO_HOURS * 3600:
                raise RuntimeError(f"That is longer than {config.MAX_VIDEO_HOURS:g} hours. Choose a shorter part of it under Options.")
            _set(job, title=meta["title"], uploader=meta["uploader"], duration=meta["duration"], views=meta.get("views"))
            if not job.get("thumb") and media.save_thumb(d, url=src["url"]):
                _set(job, thumb=True)
            usage.set_context(job["creator"], meta["title"])
            span = (o["range_end"] or meta["duration"]) - (o["range_start"] or 0)
            pieces = span > LONG_VIDEO or meta["duration"] <= 0
            if not pieces:  # shorter video: fetch all of it in the background while the audio is worked on
                video = fetch.submit(media.download, src["url"], d, int(o["quality"]), cancel)
            audio_file = media.download_audio(src["url"], d, lambda p: _set(job, progress=0.03 + 0.1 * p), cancel)
    else:
        pieces, audio_file = False, Path(src["path"])
        info = media.probe(audio_file)
        if info["duration"] > config.MAX_VIDEO_HOURS * 3600:
            raise RuntimeError(f"That video is longer than {config.MAX_VIDEO_HOURS:g} hours, which is the limit.")
        _set(job, source_path=str(audio_file), width=info["width"], height=info["height"], duration=info["duration"])
        if not job.get("thumb") and media.save_thumb(d, video=audio_file):
            _set(job, thumb=True)
    wav = d / "audio.wav"
    media.extract_audio(audio_file, wav, cancel)
    audio = media.load_audio(wav)
    wav.unlink(missing_ok=True)
    if src["type"] == "url":
        audio_file.unlink(missing_ok=True)
    if not job["duration"]:
        job["duration"] = len(audio) / 16000
    lo = int((o["range_start"] or 0) * 16000)
    hi = min(len(audio), int(o["range_end"] * 16000)) if o["range_end"] else len(audio)
    span = (hi - lo) / 16000
    db = media.loudness_per_second(audio[lo:hi])
    (d / "loudness.json").write_text(json.dumps({"values": db.tolist(), "offset": lo / 16000}), encoding="utf-8")

    vlock, vstate = threading.Lock(), {}

    def whole_video():
        """Wait for the background download once; retry it, or give up and use pieces."""
        with vlock:
            if "path" not in vstate:
                if meta.get("is_live"):
                    vstate["path"] = source_file
                    return source_file
                path = None
                try:
                    path = video.result()
                except Exception as e:  # noqa: BLE001 - sites sometimes refuse a download
                    if cancel.is_set():
                        raise RuntimeError("cancelled")
                    notes.append(f"Video download refused once ({str(e)[-80:]}), retrying")
                    try:
                        path = media.download(src["url"], d, int(o["quality"]), cancel)
                    except Exception as e2:  # noqa: BLE001
                        if cancel.is_set():
                            raise RuntimeError("cancelled")
                        notes.append(f"Whole-video download failed ({str(e2)[-80:]}), fetching clip parts instead")
                if path:
                    info = media.probe(path)
                    job.update(source_path=str(path), width=info["width"], height=info["height"])
                vstate["path"] = path
            return vstate["path"]

    exact = {}      # clip id -> (from, to, words): our own model's words for just that clip

    began = {}      # clip id -> when work on it started

    def make(clip, words_now):
        if cancel.is_set():
            clip.update(status="cancelled", error=None)
            save(job)
            return
        began[clip["id"]] = time.time()
        if src["type"] == "url" and (pieces or not whole_video()):
            _fetch_piece(job, clip, audio, cancel)
        if clip["status"] != "error" and yt and yt[1].lower().startswith("en"):
            # The clip was found with YouTube's transcript. What is shown on screen comes from our own model,
            # run on just this clip: full punctuation, nothing blanked out, timings to the word.
            a0, b0 = max(lo, int((clip["start"] - 1.5) * 16000)), min(hi, int((clip["end"] + 1.5) * 16000))
            try:
                tw = [dict(w, s=round(w["s"] + a0 / 16000, 2), e=round(w["e"] + a0 / 16000, 2)) for w in transcribe.transcribe(audio[a0:b0])]
            except Exception:  # noqa: BLE001 - the clip is still made, with YouTube's words
                tw = []
            if len(tw) >= 3:
                exact[clip["id"]] = (a0 / 16000, b0 / 16000, tw)
                words_now = tw
        if clip["status"] != "error":
            render_one(job, clip, words_now)

    cpus = os.cpu_count() or 4
    renders = ThreadPoolExecutor(2 if cpus < 8 else min(6, cpus // 6))  # more clips made at once on a bigger machine
    futures = []
    step = BLOCK * 16000 if span > PROGRESSIVE_FROM else hi - lo
    blocks = [(x, min(hi, x + step)) for x in range(lo, hi, step)] or [(lo, hi)]
    words, tokens, model = [], 0, None
    selection = {"candidates": 0, "ranked": 0, "accepted": 0, "fallback": False,
                 "fallback_windows": 0, "duration_ms": 0}
    done_blocks = 0
    yt = None
    if src["type"] == "url" and config.YT_TRANSCRIPT and media.is_youtube(src["url"]):
        try:
            yt = media.youtube_words(src["url"])
        except Exception:  # noqa: BLE001 - no transcript to borrow: ours is written as usual
            yt = None
        if yt and not _covers(yt[0], lo / 16000, hi / 16000):
            yt = None
        job["transcript_from"] = "youtube" if yt else "own"
        selected_language = o.get("speech_language") or "auto"
        job["lang"] = selected_language if selected_language != "auto" else (yt[1] if yt else "")
    if resuming:
        try:
            words = json.loads((d / "words.json").read_text(encoding="utf-8"))
        except ValueError:
            words = []
        done_blocks = min(int(job.get("done_blocks", 0)), len(blocks)) if words else 0
        tokens, model = int((job.get("ai") or {}).get("tokens", 0)), (job.get("ai") or {}).get("model")
        saved_selection = (job.get("ai") or {}).get("selection") or {}
        for key in ("candidates", "ranked", "accepted", "fallback_windows", "duration_ms"):
            selection[key] = int(saved_selection.get(key, 0) or 0)
        selection["fallback"] = bool(saved_selection.get("fallback"))
        if saved_selection.get("target_seconds"):
            selection["target_seconds"] = saved_selection["target_seconds"]
        if done_blocks < len(blocks):     # words past the last finished part are transcribed again
            cut = blocks[done_blocks][0] / 16000
            words = [w for w in words if w["s"] < cut]
        for c in job["clips"]:            # clips found before the restart that were not finished yet
            if c.get("status") not in ("done", "error"):
                c["status"] = "queued"
                futures.append((renders.submit(ctx.bind(make), c, list(words)), c))
        save(job)
    # The transcript of the next part is written while the AI is still reading this one (the AI is a wait on the
    # network, the transcript is work on this machine), so neither waits for the other.
    ahead = ThreadPoolExecutor(2, thread_name_prefix="ahead")
    heard, now_on = {}, [done_blocks]

    def hear(i):
        if i < len(blocks) and i >= done_blocks and i not in heard:
            a_, b_ = blocks[i]
            last = [0.0]

            def tp(p, i=i, a_=a_, b_=b_):
                if now_on[0] == i and p - last[0] > 0.05:      # only the part being shown moves the bar
                    last[0] = p
                    _set(job, progress=max(job["progress"], 0.14 + 0.78 * ((a_ - lo) + p * (b_ - a_)) / max(1, hi - lo)))
            heard[i] = ahead.submit(ctx.bind(transcribe.transcribe), audio[a_:b_], tp)

    for bi, (a, b) in enumerate(blocks):
        if cancel.is_set():
            break
        if bi < done_blocks:
            continue                      # transcribed and checked by the AI before the restart
        shift = a / 16000
        where = f" (minute {round((a - lo) / 16000 / 60)} of {round(span / 60)})" if len(blocks) > 1 else ""
        if yt:
            _set(job, stage="Reading the transcript" + where)
            bw = [dict(w, s=round(w["s"] - shift, 2), e=round(w["e"] - shift, 2)) for w in yt[0] if a / 16000 <= w["s"] < b / 16000]
        else:
            _set(job, stage="Writing the transcript" + where)
            now_on[0] = bi
            hear(bi)
            hear(bi + 1)
            bw = heard.pop(bi).result()
        _set(job, progress=max(job["progress"], 0.14 + 0.78 * (b - lo) / max(1, hi - lo)))
        words += [dict(w, s=round(w["s"] + shift, 2), e=round(w["e"] + shift, 2)) for w in bw]
        (d / "words.json").write_text(json.dumps(words), encoding="utf-8")
        _set(job, stage="Finding the best moments" + where, word_count=len(words))
        left = int(o["max_clips"]) - len(job["clips"])
        if left <= 0 or len(bw) < 8:
            job["done_blocks"] = bi + 1
            save(job)
            continue
        quota = max(1, math.ceil(left / (len(blocks) - bi)))
        s0 = int((a - lo) / 16000)
        found, ai = brain.find_clips(bw, db[s0: s0 + int((b - a) / 16000) + 1], (b - a) / 16000, job["title"],
                                     job["uploader"], quota, int(o["min_len"]), int(o["max_len"]), notes.append,
                                     preferences=o.get("moment_prompt", ""), speech_language=o.get("speech_language", "auto"),
                                     genre=o.get("genre", "auto"))
        tokens += ai.get("tokens", 0)
        model = ai.get("model") or model
        sel = ai.get("selection") or {}
        for key in ("candidates", "ranked", "accepted", "duration_ms"):
            selection[key] += int(sel.get(key, 0) or 0)
        selection["fallback"] = selection["fallback"] or bool(sel.get("fallback"))
        selection["fallback_windows"] += int(bool(sel.get("fallback")))
        if sel.get("target_seconds"):
            selection["target_seconds"] = sel["target_seconds"]
        if ai.get("note"):
            notes.append(ai["note"])
        for c in found:
            if not str(c.get("description") or "").strip():
                c["description"] = str(c.get("reason", "") or c.get("title", ""))
            c.setdefault("description_source", "ai" if model else "summary")
            c.setdefault("reason", c.get("description", ""))
            c.update(id=f"clip{len(job['clips']) + 1:02d}", start=round(c["start"] + shift, 2),
                     end=round(c["end"] + shift, 2), style=o["style"], layout=o["layout"],
                     aspect=o.get("aspect", DEFAULTS["aspect"]), emoji_preset=o.get("emoji_preset", DEFAULTS["emoji_preset"]),
                     emoji_frequency=o.get("emoji_frequency", DEFAULTS["emoji_frequency"]),
                     cleanup_level=o.get("cleanup_level", DEFAULTS["cleanup_level"]),
                     zoom_preset=o.get("zoom_preset", DEFAULTS["zoom_preset"]),
                     color_preset=o.get("color_preset", DEFAULTS["color_preset"]),
                     color_brightness=o.get("color_brightness", DEFAULTS["color_brightness"]),
                     color_contrast=o.get("color_contrast", DEFAULTS["color_contrast"]),
                     color_saturation=o.get("color_saturation", DEFAULTS["color_saturation"]),
                     color_sharpness=o.get("color_sharpness", DEFAULTS["color_sharpness"]),
                     transition=o.get("transition", DEFAULTS["transition"]), status="queued", version=0,
                      **{k: _bool(o.get(k, DEFAULTS[k])) for k in EFFECT_KEYS})
            job["clips"].append(c)
            futures.append((renders.submit(ctx.bind(make), c, list(words)), c))
        job["ai"] = {"model": model, "tokens": tokens, "note": "", "log": notes[-5:], "selection": selection}
        job["done_blocks"] = bi + 1       # a restart from here on carries on with the next part
        save(job)
    if futures:
        _set(job, stage="Finishing the clips", progress=max(job["progress"], 0.92))
    _wait_for_clips(job, futures, began, renders._max_workers)
    if exact:           # keep our own words for the clips in the saved transcript, so editing a clip later uses them
        for a_s, b_s, tw in exact.values():
            words = [w for w in words if not a_s <= w["s"] < b_s] + tw
        words.sort(key=lambda w: w["s"])
        (d / "words.json").write_text(json.dumps(words), encoding="utf-8")
    renders.shutdown(wait=False)
    ahead.shutdown(wait=False)
    fetch.shutdown(wait=False)
    del audio
    if cancel.is_set() or job.get("status") in ("cancelling", "cancelled"):
        _mark_pending_cancelled(job)
        _set(job, status="cancelled", stage="Cancelled by you", progress=max(job.get("progress", 0), 0.0),
             error=None, took=round(time.time() - t0))
        return
    clips = job["clips"]
    job["ai"] = {"model": model, "tokens": tokens, "log": notes[-5:], "selection": selection,
                 "note": "The AI was unavailable, so clips were ranked with deterministic transcript, audio, context and duplicate signals."
                 if clips and not model else ""}
    stage = "Done" if clips else "Done, but nothing clip-worthy was found"
    _set(job, status="done", stage=stage, progress=1.0, took=round(time.time() - t0))
    try:
        from . import notices
        name = job.get("title") or job["source"].get("name") or "your video"
        notices.add(job.get("user"), "clips", f"{len(clips)} clip{'s' if len(clips) != 1 else ''} ready" if clips else "Nothing clip-worthy found",
                    name, f"/app/creators/{job['creator']}" if job.get("creator") else "/app/videos")
    except Exception:  # noqa: BLE001
        pass
    creators.log(job["creator"], f"Video finished with {len(clips)} clips in {round(time.time() - t0)}s: {job['title']}")


def _run_more(job):
    """Search the saved transcript for additional moments and append them to the same job."""
    import numpy as np
    d = Path(job["dir"])
    ev = _event_for(_more_cancel_events, job["id"])
    more = job.setdefault("more", {"status": "idle", "progress": 0.0, "added": 0, "error": None})
    more.update(status="running", progress=0.04, added=0, error=None, note="Reading the saved transcript…")
    save(job)
    try:
        words = json.loads((d / "words.json").read_text(encoding="utf-8"))
        raw = json.loads((d / "loudness.json").read_text(encoding="utf-8")) if (d / "loudness.json").is_file() else {}
        values = raw.get("values", []) if isinstance(raw, dict) else raw
        offset = float(raw.get("offset", 0)) if isinstance(raw, dict) else 0.0
        duration = float(job.get("duration") or (max((w.get("e", 0) for w in words), default=0)))
        db = np.zeros(max(1, int(duration) + 2), dtype=np.float32)
        at = max(0, int(round(offset)))
        values = np.asarray(values, dtype=np.float32)
        db[at:at + len(values)] = values[:max(0, len(db) - at)]
        if ev.is_set():
            more.update(status="cancelled", note="Stopped by you")
            save(job)
            return
        o = {**DEFAULTS, **(job.get("options") or {})}
        existing = [c for c in job.get("clips", []) if c.get("status") != "cancelled"]
        notes = []
        more.update(progress=0.12, note="Finding moments not already used…")
        save(job)
        found, ai = brain.find_clips(words, db, duration, job.get("title", ""), job.get("uploader", ""),
                                     max(1, int(o.get("max_clips", 6))), int(o.get("min_len", 15)),
                                     int(o.get("max_len", 60)), notes.append, existing=existing,
                                     preferences=o.get("moment_prompt", ""), speech_language=o.get("speech_language", "auto"),
                                     genre=o.get("genre", "auto"))
        more.update(progress=0.62, note="Queueing new clips…")
        save(job)
        new_ids = []
        for i, c in enumerate(found):
            if ev.is_set():
                break
            cid = _next_clip_id(job)
            if not str(c.get("description") or "").strip():
                c["description"] = str(c.get("reason", "") or c.get("title", ""))
            c.setdefault("description_source", "ai" if ai.get("model") else "summary")
            c.setdefault("reason", c.get("description", ""))
            c.update(id=cid, start=round(c["start"], 2), end=round(c["end"], 2), style=o["style"],
                     layout=o["layout"], aspect=o.get("aspect", DEFAULTS["aspect"]),
                     emoji_preset=o.get("emoji_preset", DEFAULTS["emoji_preset"]),
                     emoji_frequency=o.get("emoji_frequency", DEFAULTS["emoji_frequency"]),
                     cleanup_level=o.get("cleanup_level", DEFAULTS["cleanup_level"]),
                     zoom_preset=o.get("zoom_preset", DEFAULTS["zoom_preset"]),
                     color_preset=o.get("color_preset", DEFAULTS["color_preset"]),
                     color_brightness=o.get("color_brightness", DEFAULTS["color_brightness"]),
                     color_contrast=o.get("color_contrast", DEFAULTS["color_contrast"]),
                     color_saturation=o.get("color_saturation", DEFAULTS["color_saturation"]),
                     color_sharpness=o.get("color_sharpness", DEFAULTS["color_sharpness"]),
                     transition=o.get("transition", DEFAULTS["transition"]), status="queued", version=0, more_run=True,
                     **{k: _bool(o.get(k, DEFAULTS[k])) for k in EFFECT_KEYS})
            job["clips"].append(c)
            new_ids.append(cid)
            more.update(progress=0.62 + 0.34 * (i + 1) / max(1, len(found)), added=len(new_ids))
            save(job)
            _q.put(("clip", job["id"], cid))
        if ev.is_set():
            for c in job.get("clips", []):
                if c.get("id") in new_ids and c.get("status") in ("queued", "rendering"):
                    c.update(status="cancelled", error=None)
            more.update(status="cancelled", progress=min(1.0, more.get("progress", 0)), note="Stopped by you")
        else:
            more.update(status="done", progress=1.0, note=(f"Added {len(new_ids)} new clip{'s' if len(new_ids) != 1 else ''}."
                                                            if new_ids else "No unused clip-worthy moments were found."),
                         ai=ai)
        save(job)
    except Exception as e:  # noqa: BLE001
        if ev.is_set():
            more.update(status="cancelled", note="Stopped by you", error=None)
        else:
            more.update(status="error", error=safe.friendly(e, 400), note="Extra clip search stopped")
        save(job)


def _worker(quick_only=False):
    while True:
        kind, a, cid = _q.get(quick_only)
        if kind == "fn":
            try:
                a()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            continue
        job = _jobs.get(a)
        if not job:
            if kind == "job":
                _q.done()
            continue
        token = ctx._uid.set(job["user"])  # everything this job does runs as its owner
        try:
            if kind == "job":
                if job.get("status") == "cancelled":
                    _mark_pending_cancelled(job)
                else:
                    _run_job(job)
            else:
                words = json.loads((Path(job["dir"]) / "words.json").read_text(encoding="utf-8"))
                clip = next(c for c in job["clips"] if c["id"] == cid)
                if _cancelled(job) or (clip.get("more_run") and _cancelled(job, more=True)):
                    clip.update(status="cancelled", error=None)
                    save(job)
                else:
                    render_one(job, clip, words)
        except Exception as e:  # noqa: BLE001
            (Path(job["dir"]) / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
            if kind == "job":
                if _cancelled(job):
                    _mark_pending_cancelled(job)
                    _set(job, status="cancelled", error=None, stage="Cancelled by you")
                else:
                    for c in job["clips"]:
                        if c.get("status") in ("queued", "rendering"):
                            c.update(status="error", error="The video stopped before this clip was made.")
                    _set(job, status="error", error=safe.friendly(e), stage="Stopped")
                    creators.log(job["creator"], f"Video failed: {safe.friendly(e)[:200]}")
            elif _cancelled(job) or (next((c for c in job.get("clips", []) if c.get("id") == cid), {}).get("more_run")
                                     and _cancelled(job, more=True)):
                clip = next((c for c in job.get("clips", []) if c.get("id") == cid), None)
                if clip:
                    clip.update(status="cancelled", error=None)
                    save(job)
        finally:
            ctx._uid.reset(token)
            if kind == "job":
                _q.done()


def _pick_up_after_restart():
    """Videos and single clips that were being made when the server stopped: queued again, oldest first."""
    waiting = sorted((j for j in all_jobs() if j.get("status") == "queued" and j.get("resume")), key=lambda j: j["created"])
    for j in waiting:
        _q.put(("job", j["id"], None), user=j["user"])
    for j in all_jobs():
        for cid in j.pop("remake", []):
            _q.put(("clip", j["id"], cid))
        if j.get("status") == "done":
            save(j)


def start():
    load.start()
    load_all()
    _pick_up_after_restart()
    for _ in range(max(1, config.JOB_WORKERS)):
        threading.Thread(target=_worker, daemon=True).start()
    threading.Thread(target=_worker, args=(True,), daemon=True).start()   # re-making a single clip never waits behind whole videos
    threading.Thread(target=_live_worker, daemon=True).start()
