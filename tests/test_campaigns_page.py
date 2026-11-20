"""Comprehensive tests for the Campaigns & Bounties page, backend endpoints, and suggested creators integration."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from studio.server import app
from studio import db

db.init()
client = TestClient(app, base_url="http://127.0.0.1:8765")
INDEX_PATH = ROOT / "web" / "index.html"
index_html = INDEX_PATH.read_text(encoding="utf-8")


def test_backend_live_campaigns():
    """Verify /api/campaigns/live endpoint returns campaigns catalog and stats."""
    res = client.get("/api/campaigns/live")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    data = res.json()
    assert "campaigns" in data, "Response missing 'campaigns' array"
    assert "stats" in data, "Response missing 'stats' object"

    campaigns = data["campaigns"]
    assert len(campaigns) >= 8, f"Expected at least 8 campaigns, got {len(campaigns)}"

    stats = data["stats"]
    assert stats["total_pool"] >= 80000, f"Expected total_pool >= 80000, got {stats['total_pool']}"
    assert stats["active_campaigns"] >= 8, f"Expected active_campaigns >= 8, got {stats['active_campaigns']}"
    assert stats["total_clippers"] >= 1000, f"Expected total_clippers >= 1000, got {stats['total_clippers']}"
    print("PASS /api/campaigns/live returns valid campaigns and stats")


def test_campaign_catalog_fields():
    """Verify each campaign has required properties."""
    res = client.get("/api/campaigns/live")
    data = res.json()
    required = ["id", "title", "creator_name", "platform", "platform_key", "channel_url",
                "reward_pool", "remaining_pool", "rate_per_1k", "category", "status",
                "target_platforms", "description", "requirements", "active_clippers"]
    for c in data["campaigns"]:
        for field in required:
            assert field in c, f"Campaign {c.get('id')} missing field {field}"
        assert c["rate_per_1k"] > 0, f"Expected positive payout rate for {c['id']}"
        assert c["reward_pool"] > 0, f"Expected positive reward pool for {c['id']}"
        assert c["remaining_pool"] <= c["reward_pool"], f"Remaining pool exceeds total pool for {c['id']}"
    print("PASS all campaigns have complete schema and positive payout values")


def test_campaign_filtering_and_sorting():
    """Verify search, platform filter, category filter, and sorting."""
    # Search
    res_speed = client.get("/api/campaigns/live?q=speed")
    data_speed = res_speed.json()["campaigns"]
    assert any("speed" in c["creator_name"].lower() for c in data_speed)

    # Platform filter
    res_kick = client.get("/api/campaigns/live?platform=kick")
    data_kick = res_kick.json()["campaigns"]
    assert len(data_kick) > 0
    assert all(c["platform_key"].lower() == "kick" for c in data_kick)

    # Sort by pool
    res_sort = client.get("/api/campaigns/live?sort=pool")
    data_sort = res_sort.json()["campaigns"]
    pools = [c["reward_pool"] for c in data_sort]
    assert pools == sorted(pools, reverse=True), "Expected pools in descending order"
    print("PASS campaign catalog filtering and sorting work correctly")


def test_add_creator_from_campaign():
    """Verify /api/campaigns/{id}/add-creator creates a workspace creator."""
    res = client.post("/api/campaigns/stableronaldo-gta6/add-creator")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    body = res.json()
    assert body.get("ok") is True
    assert "creator" in body
    assert body["creator"]["name"] == "StableRonaldo"
    assert body["creator"]["rate_per_1k"] == 2.50

    # Calling again should gracefully return already_exists: True
    res2 = client.post("/api/campaigns/stableronaldo-gta6/add-creator")
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2.get("already_exists") is True
    print("PASS /api/campaigns/{id}/add-creator creates workspace creator and handles duplicates")


def test_quick_add_suggested_creator():
    """Verify /api/creators/quick-add creates a streamer in user's workspace."""
    payload = {
        "name": "Asmongold",
        "channel": "https://www.twitch.tv/zackrawrr",
        "platform": "twitch"
    }
    res = client.post("/api/creators/quick-add", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    body = res.json()
    assert body.get("ok") is True
    assert "creator" in body
    assert body["creator"]["name"] == "Asmongold"
    print("PASS /api/creators/quick-add successfully adds suggested streamer")


def test_frontend_routes_and_navigation():
    """Verify campaigns route, topbar link, and sidebar navigation."""
    assert 'campaigns: "campaigns"' in index_html, "Missing campaigns in ROUTES"
    assert 'if (norm === "/app/bounties") return ["campaigns", "clips"];' in index_html
    assert 'topLink("campaigns", "money", "Campaigns"' in index_html
    assert 'nav("campaigns", navIc("money", "campaigns"), "Campaigns"' in index_html
    assert '<span class="sb-tag bounty-badge"><i></i>Hot</span>' in index_html
    print("PASS frontend routes and navigation include Campaigns")


def test_sidebar_suggested_streamers():
    """Verify sidebar renders 'Suggested for you' section with live badges and quick-add buttons."""
    assert "Suggested for you" in index_html
    assert "nav-suggested-row" in index_html
    assert "nav-suggested-add-btn" in index_html
    assert 'data-act="addsuggestedcreator"' in index_html
    assert "Asmongold" in index_html
    assert "HasanAbi" in index_html
    assert "Jynxzi" in index_html
    assert "N3on" in index_html
    assert "PlaqueBoyMax" in index_html
    print("PASS sidebar includes Suggested for you section with quick-add actions")


def test_campaigns_page_structure():
    """Verify campaigns page container, KPI stats, filters, and two-button card markup."""
    fresh_html = INDEX_PATH.read_text(encoding="utf-8")
    assert 'id="campaigns-page"' in fresh_html
    assert "drawCampaignsPage" in fresh_html
    assert "drawContentRewardsDetail" in fresh_html
    assert "loadCampaigns" in fresh_html
    assert "Live Campaigns & Bounties" in fresh_html
    assert "campaign-kpis" in fresh_html
    assert "Active Bounty Pool" in fresh_html
    assert "Active Clippers" in fresh_html
    assert "Paid to Clippers" in fresh_html
    assert 'id="campaign_search"' in fresh_html
    assert 'id="campaign_sort"' in fresh_html
    assert 'data-act="campaignfilter"' in fresh_html
    assert "🔥 High Payout ($2.50+)" in fresh_html
    assert "campaign-card" in fresh_html
    assert "payout-rate-tag" in fresh_html
    assert "Payout per 1K Views" in fresh_html
    # Exactly two buttons on card: Add Creator and Open
    assert 'data-act="campaignaddcreator"' in fresh_html
    assert 'data-act="opencampaign"' in fresh_html
    # Dedicated Content Rewards view structure
    assert "Content Rewards" in fresh_html
    assert "cr-detail-container" in fresh_html
    assert "cr-platforms-row" in fresh_html
    assert "cr-budget-track" in fresh_html
    assert "cr-locked-content-box" in fresh_html
    assert "cr-podium-grid" in fresh_html
    assert "cr-chart-container" in fresh_html
    assert 'data-act="backtocampaigns"' in fresh_html
    assert 'data-act="copycampaignurl"' in fresh_html
    print("PASS campaigns page layout, stats, filters, and Content Rewards detail view are present")


def test_event_listeners_and_css():
    """Verify event listeners and CSS styling for campaigns and suggested streamers."""
    fresh_html = INDEX_PATH.read_text(encoding="utf-8")
    assert 'if (a === "campaignfilter")' in fresh_html
    assert 'if (a === "campaignaddcreator")' in fresh_html
    assert 'if (a === "opencampaign")' in fresh_html
    assert 'if (a === "backtocampaigns")' in fresh_html
    assert 'if (a === "copycampaignurl")' in fresh_html
    assert 'if (a === "addsuggestedcreator")' in fresh_html
    assert 'if (e.target.id === "campaign_search")' in fresh_html
    assert 'if (e.target.id === "campaign_sort")' in fresh_html
    assert "#campaigns-page {" in fresh_html
    assert ".campaign-kpi-card {" in fresh_html
    assert ".campaign-card {" in fresh_html
    assert ".cr-detail-container {" in fresh_html
    assert ".cr-hero-card {" in fresh_html
    assert ".nav-suggested-row {" in fresh_html
    assert ".nav-suggested-add-btn {" in fresh_html
    print("PASS event listeners and CSS styles are fully wired")


def test_single_campaign_detail_endpoint():
    """Verify /api/campaigns/{id} returns dynamic details for Content Rewards."""
    res = client.get("/api/campaigns/womack-sisters-part2")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["id"] == "womack-sisters-part2"
    assert "The Womack Sisters" in data["title"]
    assert data["brand"] == "The Clip Ship"
    assert data["rate_per_1k"] == 1.00
    assert "platform_payouts" in data
    assert "tiktok" in data["platform_payouts"]
    assert "instagram" in data["platform_payouts"]
    assert "youtube" in data["platform_payouts"]
    assert data["remaining_pool"] > 0
    print("PASS /api/campaigns/{id} returns dynamic campaign details")


if __name__ == "__main__":
    test_backend_live_campaigns()
    test_campaign_catalog_fields()
    test_campaign_filtering_and_sorting()
    test_add_creator_from_campaign()
    test_quick_add_suggested_creator()
    test_frontend_routes_and_navigation()
    test_sidebar_suggested_streamers()
    test_campaigns_page_structure()
    test_event_listeners_and_css()
    test_single_campaign_detail_endpoint()
    print("ALL CAMPAIGNS TESTS PASSED")
