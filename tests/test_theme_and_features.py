"""Test theme consistency (no unwanted orange), creator video views, and AI descriptions."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

def test_theme_green_sliders_and_ranges():
    # Verify range slider track and thumbs use theme green, not orange
    assert ".studio-range-track i" in html
    assert "background: var(--brand" in html
    assert "#FF8B33" not in html.split(".studio-range-track")[1].split(".studio-range-controls input[type=range]::-moz-range-thumb")[0]
    print("PASS range sliders use theme green without orange track or thumbs")

def test_play_button_theme():
    # Verify play button veil and hover are theme green, not orange
    assert "background: #FF9A4C" not in html
    print("PASS play button hover is not orange")

def test_ai_descriptions_on_clips():
    # Verify clip cards render AI description box
    assert "clip-ai-desc" in html
    assert "clip-ai-tag" in html
    assert "AI Description" in html
    assert "clip-ai-text" in html
    print("PASS clip cards include AI description container at the bottom")

def test_clip_cards_stay_dark_and_summaries_are_honest():
    clip_css = html.split(".clip {", 1)[1].split(".shot {", 1)[0]
    assert "background: var(--frame-2)" in clip_css
    assert "color: var(--text)" in clip_css
    assert "description_source" in html
    assert "CLIP SUMMARY" in html
    assert "Regenerate this clip to create a short transcript summary." in html
    print("PASS clip cards use the dark theme and distinguish summaries from AI output")

def test_creator_video_views():
    # Verify creator recent videos and video jobs expose views
    assert "recent-views-badge" in html
    assert "viewsTxt" in html
    assert 'fmtK(v.views)' in html
    print("PASS creator videos and headers expose video view count")

def test_dialog_and_editor_dark_theme():
    # Verify clip editor inputs/cards are dark themed with sharp edges without breaking studio recipe
    assert "#clipdlg .editor :where(input" in html
    assert "#clipdlg .editor .feature-card" in html
    assert "border-radius: 0 !important" in html
    assert '#clipdlg [data-act="remake"]' in html
    print("PASS clip editor and dialog containers match dark theme with sharp corners")

if __name__ == "__main__":
    test_theme_green_sliders_and_ranges()
    test_play_button_theme()
    test_ai_descriptions_on_clips()
    test_clip_cards_stay_dark_and_summaries_are_honest()
    test_creator_video_views()
    test_dialog_and_editor_dark_theme()
    print("ALL THEME AND FEATURE TESTS PASSED")
