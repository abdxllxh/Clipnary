"""A creator's public profile, read from their channel link: display name, picture and follower count.

YouTube and Twitch put the name and picture in the channel page's share tags (YouTube also shows the subscriber
count there); Kick has a public JSON endpoint with all three. Twitch does not show followers publicly, so that
one comes back without a count. Everything here is best effort: a creator works the same without a profile."""
import base64
import json
import re
import threading
import time
import urllib.request
from urllib.parse import urlparse

from . import creators, ctx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
PIC_HOSTS = ("yt3.googleusercontent.com", "yt3.ggpht.com", "static-cdn.jtvnw.net", "files.kick.com")
MAX_PIC = 600_000

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="profiles")   # lookups never pile up as thousands of threads
_live: dict = {}          # channel link -> (when, result): everyone watching the same channel shares one check
_live_locks: dict = {}
LIVE_SHARED_FOR = 75      # seconds a live check is reused for every user

_cache: dict = {}
_recent_cache: dict = {}
_busy: set = set()
_tried: dict = {}
_again: set = set()
_lock = threading.Lock()


def _get(url: str, accept: str = "text/html", limit: int = 3_000_000):
    req = urllib.request.Request(url, headers={**UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.headers.get("Content-Type") or "", r.read(limit)


def _meta(html: str, prop: str):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop), html)
    return m.group(1).replace("&amp;", "&") if m else ""


def _picture(url: str):
    """The picture as (bytes, type), only from the platforms' own image hosts."""
    u = urlparse(url or "")
    if u.scheme != "https" or (u.hostname or "") not in PIC_HOSTS:
        return None
    ctype, data = _get(url, "image/*", MAX_PIC + 1)
    ctype = ctype.split(";")[0].strip()
    if ctype not in ("image/jpeg", "image/png", "image/webp") or len(data) > MAX_PIC:
        return None
    return data, ctype


def _short(n: int) -> str:
    for d, s in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= d:
            v = n / d
            return (f"{v:.1f}".rstrip("0").rstrip(".") if v < 100 else f"{v:.0f}") + s
    return str(n)


def platform_of(url: str) -> str:
    h = (urlparse(url if "://" in url else "https://" + url).hostname or "").lower()
    return "YouTube" if "youtube" in h or h == "youtu.be" else "Twitch" if "twitch" in h else "Kick" if "kick" in h else ""


def fetch(channel: str) -> dict:
    """{platform, name, followers, pic: (bytes, type) | None}. Raises if the channel can't be read."""
    url = channel.strip()
    if "://" not in url:
        url = "https://" + url
    url = re.sub(r"/(live|videos|streams|featured)/?$", "", url.split("?")[0].rstrip("/"))
    plat = platform_of(url)
    got = _cache.get(url)
    if got and time.time() - got[0] < (3600 if got[1] else 60):
        if got[1] is None:       # it failed a moment ago for someone: don't ask the platform again for every user
            raise ValueError("Couldn't find that channel. Check the link.")
        return got[1]
    try:
        return _fetch(url, plat)
    except Exception:
        _cache[url] = (time.time(), None)
        raise


def _fetch(url: str, plat: str) -> dict:
    if plat == "Kick":
        slug = urlparse(url).path.strip("/").split("/")[0]
        if not re.fullmatch(r"[\w\-]{2,40}", slug):
            raise ValueError("That doesn't look like a Kick channel link.")
        _, raw = _get(f"https://kick.com/api/v2/channels/{slug}", "application/json")
        d = json.loads(raw)
        user = d.get("user") or {}
        n = str(d.get("followers_count") or "").strip()  # Kick sends this as text
        out = {"platform": plat, "name": user.get("username") or slug,
               "followers": f"{_short(int(n))} followers" if n.isdigit() else "", "pic_url": user.get("profile_pic") or ""}
    elif plat == "Twitch" and (tw := _twitch_profile(url)):
        out = tw
    elif plat in ("YouTube", "Twitch"):
        _, raw = _get(url)
        html = raw.decode("utf-8", "replace")
        name = _meta(html, "og:title")
        if plat == "Twitch":
            name = re.sub(r"\s*-\s*(Live on )?Twitch\s*$", "", name)
        if not name or name.lower() in ("youtube", "twitch"):
            raise ValueError("Couldn't find that channel. Check the link.")
        subs = ""
        if plat == "YouTube":
            m = re.search(r'"content":"([\d.,]+[KMB]?) subscribers"', html) or re.search(r'([\d.,]+[KMB]?) subscribers', html)
            subs = f"{m.group(1)} subscribers" if m else ""
        out = {"platform": plat, "name": name[:80], "followers": subs, "pic_url": _meta(html, "og:image")}
    else:
        raise ValueError("Channel links must be from YouTube, Twitch or Kick.")
    try:
        out["pic"] = _picture(out.pop("pic_url"))
    except Exception:
        out["pic"] = None
    _cache[url] = (time.time(), out)
    if len(_cache) > 3000:
        _cache.pop(next(iter(_cache)))
    return out


def preview(channel: str) -> dict:
    """For the browser: the same, with the picture inline."""
    p = fetch(channel)
    pic = p.get("pic")
    return {"platform": p["platform"], "name": p["name"], "followers": p["followers"],
            "pic": f"data:{pic[1]};base64," + base64.b64encode(pic[0]).decode() if pic else ""}


def _video_metadata(video_url: str, ydl_module=None):
    """Read public video metadata without downloading the video itself."""
    if ydl_module is None:
        import yt_dlp as ydl_module
    from .live import _Quiet
    try:
        opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                "noplaylist": True, "socket_timeout": 12, "logger": _Quiet()}
        with ydl_module.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False) or {}
        count = info.get("view_count")
        return {"views": int(count) if count is not None else None,
                "timestamp": info.get("timestamp") or info.get("release_timestamp"),
                "duration": info.get("duration"), "thumbnail": info.get("thumbnail"),
                "title": info.get("title"), "url": info.get("webpage_url") or video_url}
    except Exception:  # noqa: BLE001 - one unavailable video must not hide the feed
        return {}


def recent_videos(channel: str, days: int = 30, limit: int = 30, force: bool = False) -> dict:
    """Return recent public source videos without downloading any media.

    This uses yt-dlp flat playlist metadata from uploads, live streams and Shorts plus
    YouTube's public RSS timestamps: it gives the creator workspace titles, upload
    timestamps, durations, thumbnails, view counts and URLs, but never fetches video
    media. Twitch and Kick public VOD feeds are handled through the same metadata path.
    """
    # Creator URLs are intentionally allowed without a scheme in the UI (for
    # example ``www.youtube.com/@name``).  yt-dlp accepts the fully qualified
    # form here, but otherwise treats the bare value as an invalid local input
    # and quietly returns an empty playlist.  Profile lookup already adds the
    # scheme; recent uploads must do the same.
    url = (channel or "").strip()
    if "://" not in url:
        url = "https://" + url
    url = url.rstrip("/")
    platform = platform_of(url)
    if platform not in ("YouTube", "Twitch", "Kick"):
        return {"videos": [], "note": "Recent public videos are available for YouTube, Twitch and Kick channels."}
    key = url.lower()
    cached = _recent_cache.get(key)
    if not force and cached and time.time() - cached[0] < 300:
        return dict(cached[1])
    from datetime import datetime, timezone, timedelta
    import yt_dlp

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(90, int(days))))
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True,
            "playlistend": max(1, min(60, int(limit) * 2)), "ignoreerrors": True, "socket_timeout": 12}
    base_url = re.sub(r"/(videos|streams|shorts)/?$", "", url, flags=re.I)
    playlist_urls = ([base_url + suffix for suffix in ("/videos", "/streams", "/shorts")]
                     if platform == "YouTube" else [base_url + "/videos"])
    entries_by_id = {}
    info = {}

    def fetch_playlist(list_url):
        try:
            # Keep each source isolated: one unavailable YouTube tab must not stop
            # the videos/streams/shorts tabs from returning what they can.
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(list_url, download=False) or {}
        except Exception:  # noqa: BLE001 - this source is best effort
            return {}

    # Do not make the browser wait for three sequential socket timeouts.  The
    # source lookups are read-only and independent, so collect whichever tabs
    # answer within the deadline and render a useful partial feed when a
    # platform is slow or rate-limited.
    playlist_futures = {_pool.submit(fetch_playlist, list_url): list_url for list_url in playlist_urls}
    try:
        for future in as_completed(playlist_futures, timeout=18):
            current = future.result() or {}
            if not info and current:
                info = current
            for entry in current.get("entries") or []:
                if entry and entry.get("id"):
                    entries_by_id[str(entry["id"])] = entry
    except TimeoutError:
        pass
    entries = list(entries_by_id.values())
    if not entries:
        raise ValueError("Couldn't load recent public videos. Check the channel link or try again later.")

    def entry_timestamp(entry: dict):
        ts = entry.get("timestamp") or entry.get("release_timestamp")
        if not ts and re.fullmatch(r"\d{8}", str(entry.get("upload_date") or "")):
            try:
                ts = datetime.strptime(str(entry["upload_date"]), "%Y%m%d").replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                ts = None
        try:
            return float(ts) if ts else None
        except (TypeError, ValueError):
            return None

    # Flat playlist extraction is quick but often omits dates. YouTube's public RSS
    # feed supplies published timestamps without an API key or video download. It is
    # intentionally best-effort: if the feed is unavailable, cards remain usable and
    # show "Recent upload" rather than blocking the whole creator page.
    channel_id = str(info.get("channel_id") or info.get("id") or "").strip()
    rss_times = {}
    if re.fullmatch(r"UC[\w-]{20,}", channel_id):
        try:
            import xml.etree.ElementTree as ET
            req = urllib.request.Request(
                f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}", headers=UA
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                root = ET.fromstring(response.read(800_000))
            atom = "{http://www.w3.org/2005/Atom}"
            yt = "{http://www.youtube.com/xml/schemas/2015}"
            for item in root.findall(f"{atom}entry"):
                vid = (item.findtext(f"{yt}videoId") or "").strip()
                published = (item.findtext(f"{atom}published") or "").strip()
                if not vid or not published:
                    continue
                try:
                    rss_times[vid] = datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
        except Exception:  # noqa: BLE001 - RSS is an optional public metadata source
            rss_times = {}
    now = datetime.now(timezone.utc)
    for entry in entries:
        vid = str(entry.get("id") or "").strip()
        if entry_timestamp(entry) is None and vid in rss_times:
            entry["timestamp"] = rss_times[vid]

    def valid_video_id(value):
        return bool(re.fullmatch(r"[\w-]{6,80}", str(value or "").strip()))

    def source_url(entry, vid):
        raw = str(entry.get("webpage_url") or entry.get("url") or "").split("#", 1)[0]
        if platform == "YouTube":
            return f"https://www.youtube.com/watch?v={vid}"
        if raw.startswith("http"):
            return raw
        if platform == "Twitch":
            return f"https://www.twitch.tv/videos/{vid.lstrip('v')}"
        return f"{base_url}/videos/{vid}"

    # Flat playlist extraction is intentionally used for the feed because it is
    # fast and never downloads media. It commonly omits dates, thumbnails or
    # views, so enrich only the missing fields with lightweight metadata lookups
    # in parallel. A failure is represented as null and rendered honestly in UI.
    detail_jobs = []
    source_urls = {}
    for entry in entries:
        vid = str(entry.get("id") or "").strip()
        if not valid_video_id(vid):
            continue
        target = source_url(entry, vid)
        source_urls[vid] = target
        if (entry.get("view_count") is None or entry_timestamp(entry) is None
                or entry.get("duration") is None or not entry.get("thumbnail")):
            detail_jobs.append((vid, target))

    details = {}
    if detail_jobs:
        def fetch_detail(item):
            return item[0], _video_metadata(item[1])

        # View counts and thumbnails are helpful enrichment, but they must not
        # block the creator page when one public video is slow to answer.
        detail_futures = {_pool.submit(fetch_detail, item): item for item in detail_jobs[:30]}
        try:
            for future in as_completed(detail_futures, timeout=10):
                try:
                    got_id, detail = future.result()
                except Exception:  # noqa: BLE001 - one video must not hide the feed
                    continue
                if got_id and detail:
                    details[got_id] = detail
        except TimeoutError:
            pass
        for entry in entries:
            vid = str(entry.get("id") or "").strip()
            detail = details.get(vid) or {}
            if not detail:
                continue
            if entry.get("timestamp") is None and detail.get("timestamp") is not None:
                entry["timestamp"] = detail["timestamp"]
            if entry.get("duration") is None and detail.get("duration") is not None:
                entry["duration"] = detail["duration"]
            if not entry.get("thumbnail") and detail.get("thumbnail"):
                entry["thumbnail"] = detail["thumbnail"]
            if entry.get("view_count") is None and detail.get("views") is not None:
                entry["view_count"] = detail["views"]

    rows = []
    have_public_times = bool(rss_times)
    for entry in entries:
        if not entry:
            continue
        vid = str(entry.get("id") or "").strip()
        if not valid_video_id(vid):
            continue
        ts = entry_timestamp(entry)
        if have_public_times and ts is None:
            # Do not label undated playlist entries as part of a 30-day window when
            # the public feed gave us a reliable timestamp for the channel.
            continue
        if ts:
            try:
                published = datetime.fromtimestamp(float(ts), timezone.utc)
                if published > now + timedelta(minutes=5) or published < cutoff:
                    continue
            except (TypeError, ValueError, OSError):
                ts = None
        title = str(entry.get("title") or (details.get(vid) or {}).get("title") or "Untitled video").strip()[:200]
        thumb = str(entry.get("thumbnail") or (details.get(vid) or {}).get("thumbnail") or "")
        if not thumb and platform == "YouTube":
            thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        raw_views = entry.get("view_count")
        try:
            views = int(raw_views) if raw_views is not None else None
        except (TypeError, ValueError):
            views = None
        rows.append({"id": vid, "title": title, "url": source_urls.get(vid) or source_url(entry, vid),
                     "thumb": thumb,
                     "timestamp": float(ts) if ts else None, "duration": entry.get("duration"),
                     "views": views, "platform": platform})
    rows.sort(key=lambda x: x["timestamp"] or 0, reverse=True)
    out = {"videos": rows[:max(1, min(30, int(limit)))], "days": max(1, min(90, int(days)))}
    _recent_cache[key] = (time.time(), out)
    if len(_recent_cache) > 500:
        _recent_cache.pop(next(iter(_recent_cache)))
    return dict(out)


LIVE_EVERY = 120        # seconds between "are they live?" checks while the app is open
PROFILE_EVERY = 86400   # name, picture and followers change rarely


# The public client id Twitch's own website uses (yt-dlp uses it too). Asks one question, gets the answer in ~1s;
# going through yt-dlp took over ten.
_TWITCH_WEB = "kimne78kx3ncx6brgo4mv6wki5h1ko"


def _twitch_live(login: str, off: dict) -> dict:
    import calendar
    import httpx
    q = 'query($l:String!){user(login:$l){login stream{title viewersCount createdAt type}}}'
    r = httpx.post("https://gql.twitch.tv/gql", json={"query": q, "variables": {"l": login}},
                   headers={"Client-ID": _TWITCH_WEB, **UA}, timeout=8)
    r.raise_for_status()
    user = ((r.json() or {}).get("data") or {}).get("user")
    if user is None:
        return off                                   # no such channel
    st = user.get("stream")
    if not st or st.get("type") != "live":
        return off
    started = None
    try:
        started = calendar.timegm(time.strptime(st["createdAt"], "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:  # noqa: BLE001
        pass
    return {"live": True, "viewers": st.get("viewersCount"), "title": (st.get("title") or "")[:140], "started": started,
            "embed": (user.get("login") or login).lower()}


def _twitch_profile(url: str):
    """Name, picture and followers from Twitch's web API (about a second; the channel page can take 30+)."""
    login = (urlparse(url).path.strip("/").split("/") or [""])[0].lower()
    if not re.fullmatch(r"\w{2,40}", login):
        return None
    try:
        import httpx
        q = 'query($l:String!){user(login:$l){login displayName profileImageURL(width:300) followers{totalCount}}}'
        r = httpx.post("https://gql.twitch.tv/gql", json={"query": q, "variables": {"l": login}},
                       headers={"Client-ID": _TWITCH_WEB, **UA}, timeout=8)
        r.raise_for_status()
        u = ((r.json() or {}).get("data") or {}).get("user")
    except Exception:  # noqa: BLE001 - the channel page is read instead
        return None
    if not u:
        return None
    n = (u.get("followers") or {}).get("totalCount")
    out = {"platform": "Twitch", "name": (u.get("displayName") or login)[:80],
           "followers": f"{_short(int(n))} followers" if isinstance(n, int) else "", "pic_url": u.get("profileImageURL") or ""}
    return out


def _ydl_info(url: str) -> dict:
    """Live details from yt-dlp without downloading anything (no formats are fetched)."""
    import yt_dlp
    if media.is_youtube(url):
        media.ensure_youtube_pot_provider()
    from .live import _Quiet
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
                           "logger": _Quiet(), "socket_timeout": 10}) as y:
        return y.extract_info(url, download=False) or {}


def _no_date(title: str) -> str:
    """yt-dlp adds the date and time to live titles; people never see that on the platform."""
    return re.sub(r"\s*\(live\)\s*\d{4}-\d{2}-\d{2} \d{2}:\d{2}$|\s+\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", "", title or "").strip()


def live_now(platform: str, url: str) -> dict:
    """{live, viewers, title, started (unix time), embed}. `embed` is what the platform's own player needs:
    the Twitch login, the YouTube video id or the Kick channel name."""
    url = url.rstrip("/")
    off = {"live": False, "viewers": None, "title": "", "started": None, "embed": ""}
    path = urlparse(url).path.strip("/").split("/")
    if platform == "Kick":
        slug = path[0]
        _, raw = _get(f"https://kick.com/api/v2/channels/{slug}", "application/json")
        ls = json.loads(raw).get("livestream")
        if not ls:
            return off
        started = None
        try:
            import calendar
            started = calendar.timegm(time.strptime(ls.get("start_time") or ls.get("created_at"), "%Y-%m-%d %H:%M:%S"))
        except Exception:
            pass
        return {"live": True, "viewers": ls.get("viewer_count"), "title": ls.get("session_title") or "", "started": started, "embed": slug}
    if platform == "YouTube":
        base = re.sub(r"/(live|videos|streams|featured)$", "", url)
        _, raw = _get(base + "/live")
        html = raw.decode("utf-8", "replace")
        if '"isLiveNow":true' not in html:
            return off
        vid = (re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html) or [None, ""])[1]
        out = {"live": True, "viewers": None, "title": _meta(html, "og:title"), "started": None, "embed": vid}
        try:
            i = _ydl_info(base + "/live")
            out.update(viewers=i.get("concurrent_view_count"), title=_no_date(i.get("title")) or out["title"],
                       started=i.get("release_timestamp") or i.get("timestamp"), embed=i.get("id") or vid)
        except Exception:
            pass
        return out
    if platform == "Twitch":
        login = (path[0] if path else "").lower()
        if re.fullmatch(r"\w{2,40}", login):
            try:
                return _twitch_live(login, off)
            except Exception:  # noqa: BLE001 - fall back to the slower way below
                pass
        try:
            i = _ydl_info(url)
        except Exception:
            return off
        if not i.get("is_live"):
            return off
        title = _no_date(i.get("title"))
        if (not title or title.lower() == (i.get("uploader_id") or "").lower()) and i.get("description"):
            title = str(i["description"]).splitlines()[0][:140]   # Twitch keeps the real stream title here
        return {"live": True, "viewers": i.get("concurrent_view_count"), "title": title,
                "started": i.get("timestamp"), "embed": (i.get("uploader_id") or path[0]).lower()}
    return off


def live_shared(platform: str, url: str) -> dict:
    """live_now, asked at most once per channel every LIVE_SHARED_FOR seconds however many people follow it.
    If a thousand users have the same creator, the platform is asked once, not a thousand times."""
    key = url.rstrip("/").lower()
    got = _live.get(key)
    if got and time.time() - got[0] < LIVE_SHARED_FOR:
        return dict(got[1])
    with _lock:
        lock = _live_locks.setdefault(key, threading.Lock())
    with lock:                                   # the first asker looks it up; the rest wait for that answer
        got = _live.get(key)
        if got and time.time() - got[0] < LIVE_SHARED_FOR:
            return dict(got[1])
        try:
            out = live_now(platform, url)
        except Exception:
            # the platform hiccuped, or the channel does not exist: keep the last answer (or "offline") for a
            # short while, so one bad channel is not asked about again for every person who follows it
            out = got[1] if got else {"live": False, "viewers": None, "title": "", "started": None, "embed": ""}
            _live[key] = (time.time() - LIVE_SHARED_FOR + 45, out)
            return dict(out)
        _live[key] = (time.time(), out)
        if len(_live) > 5000:
            for k in [k for k, v in list(_live.items()) if time.time() - v[0] > 600]:
                _live.pop(k, None)
                _live_locks.pop(k, None)
        return dict(out)


def _clean_name(c: dict) -> dict:
    """Names auto-filled while a Twitch channel was live came with ' - Live on Twitch' on the end."""
    m = re.match(r"^(.*?)\s*-\s*(Live on )?Twitch$", c.get("name") or "")
    return {"name": m.group(1)} if m and m.group(1) else {}


def _profiles(cid, c, old, lives, force, now) -> dict:
    out = {}
    for key_, url in c["channels"].items():
        prev = old.get(key_) or {}
        p = dict(prev) if prev.get("channel") == url else {}
        try:
            if force or not p or now - p.get("at", 0) > PROFILE_EVERY:
                f = fetch(url)
                pic = f.get("pic")
                if pic:
                    (creators.root(cid) / f"avatar-{key_}.img").write_bytes(pic[0])
                p.update(platform=f["platform"], name=f["name"], followers=f["followers"],
                         pic=pic[1] if pic else p.get("pic", ""), channel=url, at=now)
        except Exception:
            p.setdefault("platform", platform_of(url))
            p.setdefault("channel", url)
        try:
            p.update(lives[key_].result(timeout=30))
        except Exception:
            pass
        p["live_at"] = now
        out[key_] = p
    return out


def refresh(cid: str, force: bool = False):
    """Update every channel of a creator: profile once a day, live state every couple of minutes.
    Runs on its own thread, so it is safe to call from a request."""
    uid = ctx.uid()
    key = (uid, cid)
    with _lock:
        if key in _busy:
            if force:
                _again.add(key)  # channels changed mid-lookup: look again once this one finishes
            return
        if not force and time.time() - _tried.get(key, 0) < LIVE_EVERY - 5:
            return
        _busy.add(key)
        _tried[key] = time.time()

    def work():
        with ctx.as_user(uid):
            try:
                c = creators.get(cid)
                if not c:
                    return
                old = c.get("profiles") or {}
                out, now = {}, time.time()
                if force:
                    for url in c["channels"].values():
                        _live.pop(url.rstrip("/").lower(), None)   # asked for now: don't use an answer from before
                # "are they live?" for every channel at once, while the pictures are fetched below
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max(1, len(c["channels"]))) as ex:
                    lives = {k: ex.submit(live_shared, platform_of(u), u) for k, u in c["channels"].items()}
                    out = _profiles(cid, c, old, lives, force, now)
                creators.set_profiles(cid, out, _clean_name(c))
            except Exception:
                pass
            finally:
                with _lock:
                    _busy.discard(key)
                    rerun = key in _again
                    _again.discard(key)
                if rerun:
                    refresh(cid, force=True)

    _pool.submit(work)


def needs_refresh(c: dict) -> bool:
    ps = c.get("profiles") or {}
    now = time.time()
    for k, url in (c.get("channels") or {}).items():
        p = ps.get(k) or {}
        if p.get("channel") != url or now - p.get("at", 0) > PROFILE_EVERY or now - p.get("live_at", 0) > LIVE_EVERY:
            return True
    return False
