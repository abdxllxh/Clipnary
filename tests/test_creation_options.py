"""Focused contract checks for the creation recipe controls and backend options."""
import os
import sys
from pathlib import Path

os.environ["PEAKCUT_DATA"] = os.environ.get("PEAKCUT_DATA", "data")
os.environ["DATABASE_URL"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import jobs  # noqa: E402

fails = []

def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"   {extra}" if extra else ""))
    if not ok:
        fails.append(name)

good = jobs.clean_options({"moment_prompt": "find the clutch reaction", "speech_language": "hi", "caption_language": "ur",
                           "genre": "gaming", "range_start": 12.5, "range_end": 88,
                           "min_len": 18, "max_len": 35, "max_clips": 12,
                           "aspect": "landscape", "emoji_preset": "expressive",
                           "cleanup_level": "strong", "zoom_preset": "cinematic",
                           "color_preset": "vibrant", "color_sharpness": 70, "transition": "dip_black"})
check("custom prompt is accepted and bounded", good["moment_prompt"] == "find the clutch reaction")
check("speech language is validated", good["speech_language"] == "hi")
check("caption language is validated", good["caption_language"] == "ur")
check("genre is validated", good["genre"] == "gaming")
check("range and recommended duration reach the backend", good["range_start"] == 12.5 and good["range_end"] == 88 and good["min_len"] == 18 and good["max_len"] == 35)
check("clip limit remains capped at twelve", good["max_clips"] == 12)
check("visual and audio presets reach the backend", good["aspect"] == "landscape" and good["emoji_preset"] == "expressive" and good["cleanup_level"] == "strong" and good["zoom_preset"] == "cinematic" and good["color_preset"] == "vibrant" and good["color_sharpness"] == 70 and good["transition"] == "dip_black")
check("supported output ratios are renderer-backed", set(jobs.ASPECTS) == set(jobs.render.OUTPUT_ASPECTS))
blur_geometry = jobs.render.geometry(1920, 1080, "blur")
zoom_geometry = jobs.render.geometry(1920, 1080, "zoom")
crop_geometry = jobs.render.geometry(1920, 1080, "crop")
check("layout geometry gives box, zoom and full-width distinct scale", len({blur_geometry[1], zoom_geometry[1], crop_geometry[1]}) == 3)
check("portrait sources keep the selected box layout", jobs.render.geometry(1080, 1920, "blur")[0] == "blur")
sample_words = [{"w": "This", "s": 0.0, "e": 0.4}, {"w": "works", "s": 0.4, "e": 0.9}]
try:
    for style in jobs.render.STYLES:
        jobs.render.build_ass(sample_words, 0, 2, "Test hook", style, [], 600, 1400, False, True, {}, 1080, 1920)
    check("caption gallery styles compile into renderer ASS", True)
except Exception as exc:  # noqa: BLE001
    check("caption gallery styles compile into renderer ASS", False, str(exc))

for key, bad in (("speech_language", "klingon"), ("genre", "unknown-format"), ("aspect", "21:9"), ("transition", "wipe")):
    try:
        jobs.clean_options({key: bad})
    except ValueError:
        check(f"invalid {key} is rejected", True)
    else:
        check(f"invalid {key} is rejected", False)

html = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")
for marker in ("recipe_source", "recipe_range_start", "recipe_range_end", "recipe_language",
               "recipe_prompt", "recipe_length", "recipe_min", "recipe_max", "Caption language",
               "data-recipe-prompt", "data-recipe-style", "gallery-card", "Video layout",
               "Blurred fill", "Zoomed in", "Fill screen", "Transitions", "Picture adjustments",
               "recipe_live_preview", "recipe_range_control_fill", "range-waveform",
               "recipe_color_sharpness", "data-recipe-transition", "checkLinkPreview"):
    check(f"creation UI exposes {marker}", marker in html)
check("creation UI exposes an audio waveform timeline", "range-waveform" in html and "range-wave-bar" in html and "Audio waveform timeline" in html)
check("creation UI does not render source thumbnails in the range timeline", 'class="range-filmstrip is-placeholder"' not in html)
check("creation UI hides output ratio picker", "Output ratio" not in html and "data-recipe-aspect" not in html)

print("ALL PASSED" if not fails else f"{len(fails)} failed")
sys.exit(1 if fails else 0)
