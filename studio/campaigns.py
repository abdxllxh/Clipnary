"""Live creator bounty and clipping campaigns with Content Rewards integration.

Enables discovery of active clipping campaigns with payouts per 1k views,
one-click 'Add Creator' workspace integration, and dedicated Content Rewards campaign views.
"""
import time
from typing import List, Dict, Any, Optional

CAMPAIGNS_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "womack-sisters-part2",
        "title": "The Womack Sisters Clipping | Part 2",
        "creator_name": "The Womack Sisters",
        "creator_slug": "thewomacksisters",
        "brand": "The Clip Ship",
        "brand_url": "https://theclipship.com",
        "platform": "TikTok / IG / YouTube",
        "platform_key": "tiktok",
        "channel_url": "https://www.tiktok.com/@thewomacksisters",
        "reward_pool": 2194,
        "remaining_pool": 484,
        "paid_out": 1710,
        "rate_per_1k": 1.00,
        "min_payout": 1.00,
        "max_payout": 300.00,
        "category": "Music",
        "status": "Accepting clips",
        "color": "#F97316",
        "avatar_text": "WS",
        "min_duration": 15,
        "launched": "Launched 4 weeks ago",
        "target_platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
        "platform_payouts": {
            "tiktok": {"rate": 1.00, "min": 1.00, "max": 300.00},
            "instagram": {"rate": 1.00, "min": 1.00, "max": 300.00},
            "youtube": {"rate": 1.00, "min": 1.00, "max": 300.00},
        },
        "description": "Cut clips from the approved folder that make people feel like they are discovering The Womack Sisters first. Viewers should feel captivated by their voices, harmonies, and nostalgic soulful energy.",
        "requirements": "Cut clips from the approved folder. High audio clarity, word-by-word captions, and immediate emotional hook within the first 3 seconds. Tag @thewomacksisters and official sound.",
        "active_clippers": 36,
        "reference_files": 1,
        "artwork_gradient": "linear-gradient(135deg, #2D1A12 0%, #17100B 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "stableronaldo-gta6",
        "title": "StableRonaldo GTA 6 Trailer & IRL Bounty",
        "creator_name": "StableRonaldo",
        "creator_slug": "stableronaldo",
        "brand": "Ronaldo Entertainment",
        "brand_url": "https://www.twitch.tv/stableronaldo",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/stableronaldo",
        "reward_pool": 10000,
        "remaining_pool": 6840,
        "paid_out": 3160,
        "rate_per_1k": 2.50,
        "min_payout": 2.50,
        "max_payout": 500.00,
        "category": "Gaming",
        "status": "Accepting clips",
        "color": "#9146FF",
        "avatar_text": "SR",
        "min_duration": 30,
        "launched": "Launched 1 week ago",
        "target_platforms": ["TikTok", "YouTube Shorts", "Instagram Reels"],
        "platform_payouts": {
            "tiktok": {"rate": 2.50, "min": 2.50, "max": 500.00},
            "instagram": {"rate": 2.50, "min": 2.50, "max": 500.00},
            "youtube": {"rate": 2.50, "min": 2.50, "max": 500.00},
        },
        "description": "Clip funny reactions, GTA 6 trailer breakdowns, and viral IRL moments from StableRonaldo's daily live streams.",
        "requirements": "Must use 9:16 vertical layout with captions. Include #StableRonaldo in caption. Quality clips only.",
        "active_clippers": 142,
        "reference_files": 2,
        "artwork_gradient": "linear-gradient(135deg, #1C122C 0%, #0D0A14 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "kaicenat-amp-24hr",
        "title": "Kai Cenat AMP 24-Hour Stream Viral Bounty",
        "creator_name": "Kai Cenat",
        "creator_slug": "kaicenat",
        "brand": "AMP Collective",
        "brand_url": "https://www.twitch.tv/kaicenat",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/kaicenat",
        "reward_pool": 15000,
        "remaining_pool": 9200,
        "paid_out": 5800,
        "rate_per_1k": 3.00,
        "min_payout": 3.00,
        "max_payout": 750.00,
        "category": "Entertainment",
        "status": "Accepting clips",
        "color": "#9146FF",
        "avatar_text": "KC",
        "min_duration": 20,
        "launched": "Launched 2 weeks ago",
        "target_platforms": ["TikTok", "YouTube Shorts"],
        "platform_payouts": {
            "tiktok": {"rate": 3.00, "min": 3.00, "max": 750.00},
            "instagram": {"rate": 2.50, "min": 2.50, "max": 500.00},
            "youtube": {"rate": 3.00, "min": 3.00, "max": 750.00},
        },
        "description": "Find the funniest guest moments, screams, freestyles, and funny interactions during AMP lock-in streams.",
        "requirements": "Word-by-word captions required. Dynamic punchy edit with high energy hook in first 3s.",
        "active_clippers": 289,
        "reference_files": 3,
        "artwork_gradient": "linear-gradient(135deg, #241433 0%, #0F0914 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "ishowspeed-world-tour",
        "title": "IShowSpeed Gaming & World Tour Bounty",
        "creator_name": "IShowSpeed",
        "creator_slug": "ishowspeed",
        "brand": "Speed Live Network",
        "brand_url": "https://www.youtube.com/@ishowspeed/live",
        "platform": "YouTube",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@ishowspeed/live",
        "reward_pool": 12000,
        "remaining_pool": 5450,
        "paid_out": 6550,
        "rate_per_1k": 2.80,
        "min_payout": 2.80,
        "max_payout": 600.00,
        "category": "Gaming",
        "status": "Accepting clips",
        "color": "#FF0000",
        "avatar_text": "SPEED",
        "min_duration": 15,
        "launched": "Launched 3 weeks ago",
        "target_platforms": ["YouTube Shorts", "TikTok", "Instagram Reels"],
        "platform_payouts": {
            "tiktok": {"rate": 2.80, "min": 2.80, "max": 600.00},
            "instagram": {"rate": 2.80, "min": 2.80, "max": 600.00},
            "youtube": {"rate": 2.80, "min": 2.80, "max": 600.00},
        },
        "description": "Clip loud moments, crazy gameplay goals, rage moments, and viral fan encounters from Speed's YouTube streams.",
        "requirements": "Highlight punchline in opening 3 seconds. Sound sharp audio enhancement recommended.",
        "active_clippers": 215,
        "reference_files": 2,
        "artwork_gradient": "linear-gradient(135deg, #331010 0%, #140505 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "adinross-kick-variety",
        "title": "Adin Ross Freestyle & Guest Bounty Pool",
        "creator_name": "Adin Ross",
        "creator_slug": "adinross",
        "brand": "Kick Streaming",
        "brand_url": "https://kick.com/adinross",
        "platform": "Kick",
        "platform_key": "kick",
        "channel_url": "https://kick.com/adinross",
        "reward_pool": 20000,
        "remaining_pool": 14100,
        "paid_out": 5900,
        "rate_per_1k": 3.50,
        "min_payout": 3.50,
        "max_payout": 1000.00,
        "category": "Entertainment",
        "status": "Accepting clips",
        "color": "#53FC18",
        "avatar_text": "AR",
        "min_duration": 30,
        "launched": "Launched 2 weeks ago",
        "target_platforms": ["TikTok", "Instagram Reels", "Kick VODs"],
        "platform_payouts": {
            "tiktok": {"rate": 3.50, "min": 3.50, "max": 1000.00},
            "instagram": {"rate": 3.50, "min": 3.50, "max": 1000.00},
            "youtube": {"rate": 3.00, "min": 3.00, "max": 800.00},
        },
        "description": "Clip crazy celebrity appearances, rap freestyles, and exclusive Kick live reactions with top streamers.",
        "requirements": "Clean word-by-word captions. Dynamic zooms and sound effects encouraged.",
        "active_clippers": 310,
        "reference_files": 4,
        "artwork_gradient": "linear-gradient(135deg, #0D2610 0%, #040F06 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "kid-laroi-baby-im-back",
        "title": "The Kid LAROI - BABY I'M BACK Viral Push",
        "creator_name": "The Kid LAROI",
        "creator_slug": "thekidlaroi",
        "brand": "Columbia Records",
        "brand_url": "https://www.tiktok.com/@thekidlaroi",
        "platform": "TikTok / IG / YouTube",
        "platform_key": "tiktok",
        "channel_url": "https://www.tiktok.com/@thekidlaroi",
        "reward_pool": 5000,
        "remaining_pool": 1850,
        "paid_out": 3150,
        "rate_per_1k": 1.20,
        "min_payout": 1.20,
        "max_payout": 350.00,
        "category": "Music",
        "status": "Accepting clips",
        "color": "#EC4899",
        "avatar_text": "KL",
        "min_duration": 15,
        "launched": "Launched 2 weeks ago",
        "target_platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
        "platform_payouts": {
            "tiktok": {"rate": 1.20, "min": 1.20, "max": 350.00},
            "instagram": {"rate": 1.20, "min": 1.20, "max": 350.00},
            "youtube": {"rate": 1.20, "min": 1.20, "max": 350.00},
        },
        "description": "Clip acoustic sessions, studio snippets, and fan concerts highlighting 'BABY I'M BACK' track chorus.",
        "requirements": "Sync text animations with vocals. Use original TikTok sound.",
        "active_clippers": 48,
        "reference_files": 2,
        "artwork_gradient": "linear-gradient(135deg, #2E1325 0%, #14050F 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "ps5-pro-showcase",
        "title": "PlayStation 5 Pro Gameplay Highlights",
        "creator_name": "PlayStation",
        "creator_slug": "playstation",
        "brand": "Sony Interactive",
        "brand_url": "https://www.youtube.com/@PlayStation",
        "platform": "YouTube / TikTok",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@PlayStation",
        "reward_pool": 12000,
        "remaining_pool": 4300,
        "paid_out": 7700,
        "rate_per_1k": 2.00,
        "min_payout": 2.00,
        "max_payout": 500.00,
        "category": "Gaming",
        "status": "Accepting clips",
        "color": "#0070D1",
        "avatar_text": "PS",
        "min_duration": 20,
        "launched": "Launched 1 week ago",
        "target_platforms": ["YouTube Shorts", "TikTok"],
        "platform_payouts": {
            "tiktok": {"rate": 2.00, "min": 2.00, "max": 500.00},
            "instagram": {"rate": 1.80, "min": 1.80, "max": 400.00},
            "youtube": {"rate": 2.00, "min": 2.00, "max": 500.00},
        },
        "description": "High-fidelity graphics comparisons, ray tracing showcase moments, and 60FPS fluid action clips.",
        "requirements": "Vertical 9:16 format with high bitrate. Clear side-by-side or zoomed feature highlights.",
        "active_clippers": 82,
        "reference_files": 1,
        "artwork_gradient": "linear-gradient(135deg, #091C36 0%, #030A14 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "redbull-dance-style",
        "title": "Red Bull Dance Your Style Finals Highlights",
        "creator_name": "Red Bull",
        "creator_slug": "redbull",
        "brand": "Red Bull Media",
        "brand_url": "https://www.tiktok.com/@redbull",
        "platform": "TikTok / IG",
        "platform_key": "tiktok",
        "channel_url": "https://www.tiktok.com/@redbull",
        "reward_pool": 8000,
        "remaining_pool": 2950,
        "paid_out": 5050,
        "rate_per_1k": 1.50,
        "min_payout": 1.50,
        "max_payout": 400.00,
        "category": "Entertainment",
        "status": "Accepting clips",
        "color": "#DB0A40",
        "avatar_text": "RB",
        "min_duration": 15,
        "launched": "Launched 3 weeks ago",
        "target_platforms": ["TikTok", "Instagram Reels"],
        "platform_payouts": {
            "tiktok": {"rate": 1.50, "min": 1.50, "max": 400.00},
            "instagram": {"rate": 1.50, "min": 1.50, "max": 400.00},
            "youtube": {"rate": 1.20, "min": 1.20, "max": 300.00},
        },
        "description": "Insane dance battles, crowd vote reactions, and explosive freestyle moves from international finalists.",
        "requirements": "Keep dancer full height in frame. Dynamic beat cuts and bold captions.",
        "active_clippers": 54,
        "reference_files": 2,
        "artwork_gradient": "linear-gradient(135deg, #2E0B14 0%, #140407 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "breeze-ai-dev",
        "title": "Breeze AI Developer Tool Launch Bounties",
        "creator_name": "Breeze AI",
        "creator_slug": "breezeai",
        "brand": "Breeze Tech",
        "brand_url": "https://www.youtube.com/@breezeai",
        "platform": "YouTube / TikTok",
        "platform_key": "youtube",
        "channel_url": "https://www.youtube.com/@breezeai",
        "reward_pool": 7500,
        "remaining_pool": 3100,
        "paid_out": 4400,
        "rate_per_1k": 3.00,
        "min_payout": 3.00,
        "max_payout": 700.00,
        "category": "Tech",
        "status": "Accepting clips",
        "color": "#06B6D4",
        "avatar_text": "BZ",
        "min_duration": 30,
        "launched": "Launched 1 week ago",
        "target_platforms": ["YouTube Shorts", "TikTok"],
        "platform_payouts": {
            "tiktok": {"rate": 3.00, "min": 3.00, "max": 700.00},
            "instagram": {"rate": 2.50, "min": 2.50, "max": 500.00},
            "youtube": {"rate": 3.00, "min": 3.00, "max": 700.00},
        },
        "description": "Clip developer productivity demos, one-click code generation magic, and terminal shortcuts.",
        "requirements": "Clear readable code text. High-contrast captions and sharp transitions.",
        "active_clippers": 42,
        "reference_files": 1,
        "artwork_gradient": "linear-gradient(135deg, #09282D 0%, #031012 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "gymshark-workout",
        "title": "Gymshark Athlete Workout Series & PRs",
        "creator_name": "Gymshark",
        "creator_slug": "gymshark",
        "brand": "Gymshark Global",
        "brand_url": "https://www.tiktok.com/@gymshark",
        "platform": "TikTok / IG",
        "platform_key": "tiktok",
        "channel_url": "https://www.tiktok.com/@gymshark",
        "reward_pool": 9000,
        "remaining_pool": 3400,
        "paid_out": 5600,
        "rate_per_1k": 1.80,
        "min_payout": 1.80,
        "max_payout": 450.00,
        "category": "Sports",
        "status": "Accepting clips",
        "color": "#10B981",
        "avatar_text": "GS",
        "min_duration": 15,
        "launched": "Launched 2 weeks ago",
        "target_platforms": ["TikTok", "Instagram Reels"],
        "platform_payouts": {
            "tiktok": {"rate": 1.80, "min": 1.80, "max": 450.00},
            "instagram": {"rate": 1.80, "min": 1.80, "max": 450.00},
            "youtube": {"rate": 1.50, "min": 1.50, "max": 350.00},
        },
        "description": "Clip motivational gym PRs, athlete form breakdowns, and high-energy workout beats.",
        "requirements": "Use energetic captions. Tag @gymshark and athlete profile.",
        "active_clippers": 61,
        "reference_files": 2,
        "artwork_gradient": "linear-gradient(135deg, #0A261C 0%, #04100B 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "jynxzi-r6-tourney",
        "title": "Jynxzi Rainbow Six Siege 1v1 Tourney Rewards",
        "creator_name": "Jynxzi",
        "creator_slug": "jynxzi",
        "brand": "Jynxzi Army",
        "brand_url": "https://www.twitch.tv/jynxzi",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/jynxzi",
        "reward_pool": 8000,
        "remaining_pool": 4120,
        "paid_out": 3880,
        "rate_per_1k": 2.20,
        "min_payout": 2.20,
        "max_payout": 550.00,
        "category": "Gaming",
        "status": "Accepting clips",
        "color": "#9146FF",
        "avatar_text": "JZ",
        "min_duration": 25,
        "launched": "Launched 3 weeks ago",
        "target_platforms": ["TikTok", "YouTube Shorts"],
        "platform_payouts": {
            "tiktok": {"rate": 2.20, "min": 2.20, "max": 550.00},
            "instagram": {"rate": 2.00, "min": 2.00, "max": 450.00},
            "youtube": {"rate": 2.20, "min": 2.20, "max": 550.00},
        },
        "description": "Clip insane clutch rounds, scream moments, headset slams, and spicy trash talk with competitive pros.",
        "requirements": "Include killcams and facecam reactions. High framerate vertical format.",
        "active_clippers": 164,
        "reference_files": 1,
        "artwork_gradient": "linear-gradient(135deg, #1C122C 0%, #0D0A14 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
    {
        "id": "asmongold-gaming-news",
        "title": "Asmongold Gaming Industry News & Debates",
        "creator_name": "Asmongold",
        "creator_slug": "asmongold",
        "brand": "OTK Network",
        "brand_url": "https://www.twitch.tv/zackrawrr",
        "platform": "Twitch",
        "platform_key": "twitch",
        "channel_url": "https://www.twitch.tv/zackrawrr",
        "reward_pool": 7500,
        "remaining_pool": 3800,
        "paid_out": 3700,
        "rate_per_1k": 2.00,
        "min_payout": 2.00,
        "max_payout": 450.00,
        "category": "Entertainment",
        "status": "Accepting clips",
        "color": "#9146FF",
        "avatar_text": "AG",
        "min_duration": 45,
        "launched": "Launched 4 weeks ago",
        "target_platforms": ["YouTube Shorts", "TikTok"],
        "platform_payouts": {
            "tiktok": {"rate": 2.00, "min": 2.00, "max": 450.00},
            "instagram": {"rate": 1.80, "min": 1.80, "max": 350.00},
            "youtube": {"rate": 2.00, "min": 2.00, "max": 450.00},
        },
        "description": "Clip sharp industry takes, controversy breakdowns, and spicy gaming community opinions.",
        "requirements": "Word-by-word captions with clear hook in title. Context-rich highlights.",
        "active_clippers": 98,
        "reference_files": 1,
        "artwork_gradient": "linear-gradient(135deg, #1A1822 0%, #0C0B10 100%)",
        "top_clippers": [
            {"rank": 1, "badge": "1", "name": "Hidden until you join"},
            {"rank": 2, "badge": "2", "name": "Hidden until you join"},
            {"rank": 3, "badge": "3", "name": "Hidden until you join"},
        ],
    },
]


def _get_dynamic_campaign(camp: Dict[str, Any], hour_tick: int) -> Dict[str, Any]:
    """Compute dynamic time-based variations so campaigns update hourly with fresh activity."""
    c = dict(camp)
    seed = (hash(c["id"]) + hour_tick) % 100
    # Simulate hourly activity and budget payout progression
    delta_clippers = (seed % 7) - 3
    c["active_clippers"] = max(12, c["active_clippers"] + delta_clippers)

    delta_budget = (seed % 15) * 8
    remaining = max(120, c["remaining_pool"] - delta_budget)
    c["remaining_pool"] = remaining
    c["paid_out"] = c["reward_pool"] - remaining

    # Provide formatted platform breakdown
    if "platform_payouts" not in c:
        rate = c.get("rate_per_1k", 2.0)
        c["platform_payouts"] = {
            "tiktok": {"rate": rate, "min": 1.00, "max": 300.00},
            "instagram": {"rate": rate, "min": 1.00, "max": 300.00},
            "youtube": {"rate": rate, "min": 1.00, "max": 300.00},
        }
    return c


def list_campaigns(
    q: str = "",
    platform: str = "",
    category: str = "",
    sort: str = "payout",
) -> Dict[str, Any]:
    """Return active live campaigns with dynamic hourly updates.

    Sort options:
      - 'payout': Highest payout per 1k views first ("Highest Pay")
      - 'remaining': Most remaining funds first ("Most Budget Remaining")
      - 'newest': Newest campaigns first
      - 'pool': Highest total reward pool first
    """
    hour_tick = int(time.time() // 3600)
    items = [_get_dynamic_campaign(c, hour_tick) for c in CAMPAIGNS_CATALOG]

    if q:
        ql = q.strip().lower()
        items = [
            c for c in items
            if ql in c["title"].lower()
            or ql in c["creator_name"].lower()
            or ql in c.get("brand", "").lower()
            or ql in c["category"].lower()
        ]

    if platform and platform.lower() not in ("all", "everything"):
        plat = platform.strip().lower()
        items = [c for c in items if plat in c["platform_key"].lower() or plat in c.get("platform", "").lower()]

    if category and category.lower() not in ("all", "everything"):
        cat = category.strip().lower()
        items = [c for c in items if cat in c["category"].lower()]

    if sort in ("remaining", "budget"):
        items.sort(key=lambda c: c["remaining_pool"], reverse=True)
    elif sort == "newest":
        items.sort(key=lambda c: (c.get("id") == "womack-sisters-part2", c.get("remaining_pool")), reverse=True)
    elif sort == "pool":
        items.sort(key=lambda c: c["reward_pool"], reverse=True)
    else:  # default 'payout' ("Highest Pay")
        items.sort(key=lambda c: c["rate_per_1k"], reverse=True)

    total_pool = sum(c["reward_pool"] for c in items)
    total_paid = sum(c["paid_out"] for c in items)
    total_clippers = sum(c["active_clippers"] for c in items)

    return {
        "campaigns": items,
        "total": len(items),
        "stats": {
            "total_pool": total_pool,
            "total_paid": total_paid,
            "total_clippers": total_clippers,
            "active_campaigns": len(items),
        },
        "timestamp": int(time.time()),
        "update_interval_hours": 1,
    }


def find_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Find a campaign by ID and return its dynamic state."""
    raw = next((c for c in CAMPAIGNS_CATALOG if c["id"] == campaign_id), None)
    if not raw:
        return None
    hour_tick = int(time.time() // 3600)
    return _get_dynamic_campaign(raw, hour_tick)
