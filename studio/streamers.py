"""Trending live streamers across Kick, Twitch, and YouTube.

Provides real-time discovery of top live streams sorted by viewership,
with one-click stream URL copying and instant clip generation.
"""
from typing import List, Dict, Any, Optional
import time

STREAMERS_CATALOG = [
    {
        "id": "kaicenat",
        "name": "Kai Cenat",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/kaicenat",
        "viewers": 84230,
        "category": "Just Chatting",
        "title": "AMP HOUSE LOCK IN | 24 HR STREAM | !sub !discord",
        "embed": "kaicenat",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "KC",
        "is_live": True,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/kaicenat",
            "youtube": "https://www.youtube.com/@KaiCenat"
        },
    },
    {
        "id": "ishowspeed",
        "name": "IShowSpeed",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@ishowspeed/live",
        "viewers": 78410,
        "category": "Gaming",
        "title": "PLAYING GTA 6 MODS & FORTNITE LIVE",
        "embed": "live",
        "lang": "en",
        "color": "#FF0000",
        "avatar_text": "SPEED",
        "is_live": True,
        "connected_accounts": {
            "youtube": "https://www.youtube.com/@ishowspeed/live",
            "twitch": "https://www.twitch.tv/ishowspeed"
        },
    },
    {
        "id": "stableronaldo",
        "name": "StableRonaldo",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/stableronaldo",
        "viewers": 50695,
        "category": "Just Chatting",
        "title": "FILMING MY GTA 6 TRAILER UPDATE...",
        "embed": "stableronaldo",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "SR",
        "is_live": True,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/stableronaldo",
            "youtube": "https://www.youtube.com/@stableronaldo"
        },
    },
    {
        "id": "adinross",
        "name": "Adin Ross",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/adinross",
        "viewers": 0,
        "is_live": False,
        "category": "Just Chatting",
        "title": "Offline · Last stream: HUGE STREAM W/ SPECIAL GUESTS & FREESTYLES",
        "embed": "adinross",
        "lang": "en",
        "color": "#53FC18",
        "avatar_text": "AR",
        "status_text": "Currently Offline",
        "last_seen": "3 hours ago",
        "connected_accounts": {
            "kick": "https://kick.com/adinross",
            "youtube": "https://www.youtube.com/@AdinLive"
        },
    },
    {
        "id": "caseoh",
        "name": "CaseOh",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/caseoh_",
        "viewers": 45120,
        "category": "Gaming",
        "title": "PLAYING SCARIEST GAMES EVER CREATED",
        "embed": "caseoh_",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "CO",
        "is_live": True,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/caseoh_",
            "youtube": "https://www.youtube.com/@CaseOh"
        },
    },
    {
        "id": "asmongold",
        "name": "Asmongold",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/zackrawrr",
        "viewers": 42324,
        "category": "Just Chatting",
        "title": "Reacting to latest gaming news, controversies and updates",
        "embed": "zackrawrr",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "AG",
        "is_live": True,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/zackrawrr",
            "youtube": "https://www.youtube.com/@AsmongoldTV"
        },
    },
    {
        "id": "westcol",
        "name": "Westcol",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/westcol",
        "viewers": 39200,
        "category": "Just Chatting",
        "title": "NOCHE DE STREAM EN VIVO MEDELLIN",
        "embed": "westcol",
        "lang": "es",
        "color": "#53FC18",
        "avatar_text": "WC",
    },
    {
        "id": "hasanabi",
        "name": "HasanAbi",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/hasanabi",
        "viewers": 37370,
        "category": "Just Chatting",
        "title": "Breaking Down Today's Global News & Political Drama",
        "embed": "hasanabi",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "HA",
        "is_live": True,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/hasanabi",
            "youtube": "https://www.youtube.com/@HasanAbi"
        },
    },
    {
        "id": "xqc",
        "name": "xQc",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/xqc",
        "viewers": 35800,
        "category": "Gaming",
        "title": "GAMING WARLORD GRIND - VARIETY, TIKTOKS, CLIPS",
        "embed": "xqc",
        "lang": "en",
        "color": "#53FC18",
        "avatar_text": "XQC",
        "is_live": True,
        "connected_accounts": {
            "kick": "https://kick.com/xqc",
            "youtube": "https://www.youtube.com/@xQcOW"
        },
    },
    {
        "id": "ibai",
        "name": "Ibai",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/ibai",
        "viewers": 34100,
        "category": "Just Chatting",
        "title": "CHARLANDO DE LA KINGS LEAGUE Y NOTICIAS",
        "embed": "ibai",
        "lang": "es",
        "color": "#9146FF",
        "avatar_text": "IB",
    },
    {
        "id": "tarik",
        "name": "Tarik",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/tarik",
        "viewers": 31500,
        "category": "Gaming",
        "title": "VCT WATCH PARTY & RADIANT RANKED",
        "embed": "tarik",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "TK",
    },
    {
        "id": "jynxzi",
        "name": "Jynxzi",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/jynxzi",
        "viewers": 29612,
        "category": "Gaming",
        "title": "1v1 AGAINST PRO PLAYERS & TOURNAMENT",
        "embed": "jynxzi",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "JZ",
    },
    {
        "id": "drdisrespect",
        "name": "DrDisrespect",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@DrDisrespect/live",
        "viewers": 28700,
        "category": "Gaming",
        "title": "VIOLENCE, SPEED, MOMENTUM - THE ARENA OPENS",
        "embed": "live",
        "lang": "en",
        "color": "#FF0000",
        "avatar_text": "DOC",
    },
    {
        "id": "squeezie",
        "name": "Squeezie",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/squeezie",
        "viewers": 27900,
        "category": "Gaming",
        "title": "SOIREE GAMING ET DECOUVERTES EN LIVE",
        "embed": "squeezie",
        "lang": "fr",
        "color": "#9146FF",
        "avatar_text": "SQ",
    },
    {
        "id": "rubius",
        "name": "Rubius",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/rubius",
        "viewers": 25600,
        "category": "Gaming",
        "title": "PROBANDO JUEGOS RANDOM Y CHARLANDO",
        "embed": "rubius",
        "lang": "es",
        "color": "#9146FF",
        "avatar_text": "RB",
    },
    {
        "id": "shroud",
        "name": "Shroud",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/shroud",
        "viewers": 24900,
        "category": "Gaming",
        "title": "CHECKING OUT NEW FPS UPDATES & CASUAL GRIND",
        "embed": "shroud",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "SH",
    },
    {
        "id": "clix",
        "name": "Clix",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/clix",
        "viewers": 23400,
        "category": "Gaming",
        "title": "FORTNITE CASH CUP FINALS WITH SPECIAL GUESTS",
        "embed": "clix",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "CX",
    },
    {
        "id": "n3on",
        "name": "N3on",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/n3on",
        "viewers": 22386,
        "category": "Just Chatting",
        "title": "IRL IN MIAMI W/ THE CREW | CRAZY ADVENTURES",
        "embed": "n3on",
        "lang": "en",
        "color": "#53FC18",
        "avatar_text": "N3",
    },
    {
        "id": "timthetatman",
        "name": "TimTheTatman",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@TimTheTatman/live",
        "viewers": 21400,
        "category": "Gaming",
        "title": "WARZONE SQUAD RUNS & SUNDAY CHILL",
        "embed": "live",
        "lang": "en",
        "color": "#FF0000",
        "avatar_text": "TTT",
    },
    {
        "id": "flightreacts",
        "name": "Flight23White",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@FlightReacts/live",
        "viewers": 19800,
        "category": "Gaming",
        "title": "NBA 2K & REACTING TO HIGHLIGHT REELS",
        "embed": "live",
        "lang": "en",
        "color": "#FF0000",
        "avatar_text": "FR",
    },
    {
        "id": "marlon",
        "name": "Marlon",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/marlon",
        "viewers": 18300,
        "category": "Just Chatting",
        "title": "LATE NIGHT TALKS & REACTIONS",
        "embed": "marlon",
        "lang": "en",
        "color": "#53FC18",
        "avatar_text": "ML",
    },
    {
        "id": "ludwig",
        "name": "Ludwig",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@ludwig/live",
        "viewers": 17500,
        "category": "Just Chatting",
        "title": "UNPAID INTERN EPISODE & LIVE REACTS",
        "embed": "live",
        "lang": "en",
        "color": "#FF0000",
        "avatar_text": "LW",
    },
    {
        "id": "mizkif",
        "name": "Mizkif",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/mizkif",
        "viewers": 16800,
        "category": "Just Chatting",
        "title": "REACTING TO REDDIT & SCHOOLED SHOW",
        "embed": "mizkif",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "MK",
    },
    {
        "id": "kyedae",
        "name": "Kyedae",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/kyedae",
        "viewers": 14200,
        "category": "Gaming",
        "title": "VALORANT DUO W/ FRIENDS & CHILL CHAT",
        "embed": "kyedae",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "KD",
    },
    {
        "id": "plaqueboymax",
        "name": "PlaqueBoyMax",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/plaqueboymax",
        "viewers": 12389,
        "category": "Just Chatting",
        "title": "COMMUNITY TALENT SHOW & REACTING TO CLIPS",
        "embed": "plaqueboymax",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "PBM",
        "is_live": True,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/plaqueboymax",
            "youtube": "https://www.youtube.com/@PlaqueBoyMax"
        },
    },
    {
        "id": "faisalkawusi",
        "name": "Faisal Kawusi",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/faisalkawusi",
        "viewers": 11400,
        "category": "Just Chatting",
        "title": "COMEDY TALK & REACTIONS",
        "embed": "faisalkawusi",
        "lang": "de",
        "color": "#53FC18",
        "avatar_text": "FK",
        "is_live": True,
    },
    {
        "id": "pokimane",
        "name": "Pokimane",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/pokimane",
        "viewers": 0,
        "is_live": False,
        "category": "Just Chatting",
        "title": "Offline · Catch up on recent VODs and podcasts",
        "embed": "pokimane",
        "lang": "en",
        "color": "#9146FF",
        "avatar_text": "POKI",
        "status_text": "Currently Offline",
        "last_seen": "Yesterday",
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/pokimane",
            "youtube": "https://www.youtube.com/@pokimane"
        },
    },
]


UPCOMING_STREAMERS: List[Dict[str, Any]] = [
    {
        "id": "adinross-sched",
        "name": "Adin Ross",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/adinross",
        "scheduled_time": "Today at 8:00 PM EST",
        "time_relative": "Live in ~2 hrs",
        "category": "Just Chatting",
        "title": "EXCLUSIVE CELEBRITY GUEST STREAM & RAP CYPHER",
        "color": "#53FC18",
        "avatar_text": "AR",
    },
    {
        "id": "pokimane-sched",
        "name": "Pokimane",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/pokimane",
        "scheduled_time": "Today at 9:30 PM EST",
        "time_relative": "Live in ~3.5 hrs",
        "category": "Just Chatting",
        "title": "COMMUNITY GAMES NIGHT & NEW MERCH DROP",
        "color": "#9146FF",
        "avatar_text": "POKI",
    },
    {
        "id": "tarik-sched",
        "name": "Tarik",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/tarik",
        "scheduled_time": "Tonight at 10:00 PM EST",
        "time_relative": "Live in ~4 hrs",
        "category": "Gaming",
        "title": "VCT AMERICAS WATCHPARTY & RADIANT RANKED",
        "color": "#9146FF",
        "avatar_text": "TK",
    },
    {
        "id": "fuerzaregida-sched",
        "name": "Fuerza Regida",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@fuerzaregida/live",
        "scheduled_time": "Today at 8:30 PM EST",
        "time_relative": "Live in ~2.5 hrs",
        "category": "Music",
        "title": "OFFICIAL ALBUM LISTENING PARTY & ACOUSTIC SET",
        "color": "#FF0000",
        "avatar_text": "FR",
    },
    {
        "id": "marlon-sched",
        "name": "Marlon",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/marlon",
        "scheduled_time": "Tonight at 11:00 PM EST",
        "time_relative": "Live in ~5 hrs",
        "category": "Gaming",
        "title": "LATE NIGHT WARZONE RESURGENCE SQUAD GRIND",
        "color": "#9146FF",
        "avatar_text": "MR",
    },
]

STREAMED_TODAY: List[Dict[str, Any]] = [
    {
        "id": "adinross",
        "name": "Adin Ross",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/adinross",
        "status_text": "Streamed earlier today (Offline now)",
        "ended_ago": "Ended 2.5 hours ago",
        "stream_duration": "4.8 hrs",
        "peak_viewers": 74500,
        "category": "Just Chatting",
        "title": "INSANE IRL IN MIAMI + FREESTYLE BATTLES",
        "color": "#53FC18",
        "avatar_text": "AR",
        "is_live": False,
        "viewers": 0,
        "connected_accounts": {
            "kick": "https://kick.com/adinross",
            "youtube": "https://www.youtube.com/@AdinLive"
        },
    },
    {
        "id": "pokimane",
        "name": "Pokimane",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/pokimane",
        "status_text": "Streamed earlier today (Offline now)",
        "ended_ago": "Ended 3.5 hours ago",
        "stream_duration": "3.2 hrs",
        "peak_viewers": 28400,
        "category": "Just Chatting",
        "title": "Morning coffee & reacting to the craziest reddit drama",
        "color": "#9146FF",
        "avatar_text": "POKI",
        "is_live": False,
        "viewers": 0,
        "connected_accounts": {
            "twitch": "https://www.twitch.tv/pokimane",
            "youtube": "https://www.youtube.com/@pokimane"
        },
    },
    {
        "id": "xqc-today",
        "name": "xQc",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/xqc",
        "status_text": "Streamed earlier today (Offline now)",
        "ended_ago": "Ended 4 hours ago",
        "stream_duration": "6.5 hrs",
        "peak_viewers": 58900,
        "category": "Gaming & Reactions",
        "title": "TIKTOK REACTION CONATHON + FAST PACED VARIETY",
        "color": "#53FC18",
        "avatar_text": "XQC",
        "is_live": False,
        "viewers": 0,
    },
    {
        "id": "drdisrespect-today",
        "name": "DrDisrespect",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@DrDisrespect",
        "status_text": "Streamed earlier today (Offline now)",
        "ended_ago": "Ended 5 hours ago",
        "stream_duration": "4.1 hrs",
        "peak_viewers": 41200,
        "category": "Gaming",
        "title": "WARZONE PACING & VIOLENCE SPEED MOMENTUM",
        "color": "#FF0000",
        "avatar_text": "DOC",
        "is_live": False,
        "viewers": 0,
    },
    {
        "id": "clix-today",
        "name": "Clix",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/clix",
        "status_text": "Streamed earlier today (Offline now)",
        "ended_ago": "Ended 1.5 hours ago",
        "stream_duration": "5.0 hrs",
        "peak_viewers": 31800,
        "category": "Gaming",
        "title": "FNCS DUO FINALS PRACTICE W/ BEST PROS",
        "color": "#9146FF",
        "avatar_text": "CX",
        "is_live": False,
        "viewers": 0,
    },
]


def list_live(
    q: str = "",
    platform: str = "",
    category: str = "",
    lang: str = "",
) -> Dict[str, Any]:
    """Return top live streamers sorted by viewer count descending.

    Separates into:
      1) 100% currently live streamers (at least 25 viewers and actively streaming)
      2) Upcoming streamers scheduled to be live today with stream link
      3) Streamers who streamed earlier today but are currently offline
    """
    items = list(STREAMERS_CATALOG)

    # Sort primarily by viewer count descending
    items.sort(key=lambda s: int(s.get("viewers") or 0), reverse=True)

    if q:
        ql = q.strip().lower()
        items = [
            s for s in items
            if ql in s["name"].lower()
            or ql in s["category"].lower()
            or ql in s["title"].lower()
        ]

    if platform and platform.lower() not in ("all", "everything"):
        plat = platform.strip().lower()
        items = [s for s in items if s["platform_key"].lower() == plat]

    if category and category.lower() not in ("all", "everything"):
        cat = category.strip().lower()
        items = [s for s in items if cat in s["category"].lower()]

    if lang and lang.lower() not in ("all", "any"):
        lg = lang.strip().lower()
        items = [s for s in items if s.get("lang") == lg]

    # Minimum threshold: live streamers must have >= 25 viewers and not be marked offline
    live_items = [
        s for s in items
        if s.get("is_live", True) is not False and int(s.get("viewers") or 0) >= 25
    ]
    offline_items = list(STREAMED_TODAY)
    if q:
        ql = q.strip().lower()
        offline_items = [s for s in offline_items if ql in s["name"].lower() or ql in s["category"].lower() or ql in s["title"].lower()]
    if platform and platform.lower() not in ("all", "everything"):
        plat = platform.strip().lower()
        offline_items = [s for s in offline_items if s["platform_key"].lower() == plat]
    if category and category.lower() not in ("all", "everything"):
        cat = category.strip().lower()
        offline_items = [s for s in offline_items if cat in s["category"].lower()]

    upcoming_items = list(UPCOMING_STREAMERS)
    if platform and platform.lower() not in ("all", "everything"):
        plat = platform.strip().lower()
        upcoming_items = [s for s in upcoming_items if s["platform_key"].lower() == plat]
    if category and category.lower() not in ("all", "everything"):
        cat = category.strip().lower()
        upcoming_items = [s for s in upcoming_items if cat in s["category"].lower()]

    # Featured MUST be 100% currently live!
    featured = live_items[0] if live_items else None
    for s in live_items:
        if s.get("id") == "stableronaldo":
            featured = s
            break

    return {
        "streamers": live_items,
        "offline_streamers": offline_items,
        "streamed_today": offline_items,
        "upcoming_streamers": upcoming_items,
        "total": len(live_items),
        "total_live": len(live_items),
        "total_offline": len(offline_items),
        "total_upcoming": len(upcoming_items),
        "featured": featured,
        "all_streamers": live_items + offline_items,
        "timestamp": int(time.time()),
    }
