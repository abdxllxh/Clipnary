"""Turns a time range into a vertical clip: 9:16 layout, bouncy word captions, hook title, cover."""
import re
import shutil
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from . import config, roman
from .media import run

W, H = config.OUT_W, config.OUT_H

# ASS colours are &HBBGGRR. `size` is the ASS font size (line height); _Font turns it into real pixels.
STYLES = {
    "bounce": {"label": "Clean Bold", "font": "Poppins ExtraBold", "size": 132, "base": "FFFFFF", "active": "00F0FF",
               "strong": "FFFFFF", "outline": 7, "pop": 112, "upper": True, "per": 3},
    "hype": {"label": "Gaming Reactions", "font": "Anton", "size": 152, "base": "FFFFFF", "active": "3C3CFF",
             "strong": "00D7FF", "outline": 7, "pop": 114, "upper": True, "per": 2},
    "clean": {"label": "Minimal White", "font": "Poppins ExtraBold", "size": 100, "base": "FFFFFF", "active": "6BD7FF",
              "strong": "FFFFFF", "outline": 5, "pop": 106, "upper": False, "per": 4},
    "karaoke": {"label": "Karaoke Highlight", "font": "Poppins ExtraBold", "size": 112, "base": "FFFFFF", "active": "00D7FF",
                "strong": "00D7FF", "outline": 6, "pop": 108, "upper": True, "per": 4},
    "word_pop": {"label": "Word Pop", "font": "Anton", "size": 144, "base": "FFFFFF", "active": "7AFF5C",
                 "strong": "7AFF5C", "outline": 8, "pop": 118, "upper": True, "per": 2},
    "yellow": {"label": "Yellow Keyword", "font": "Poppins ExtraBold", "size": 124, "base": "FFFFFF", "active": "00D7FF",
               "strong": "00D7FF", "outline": 7, "pop": 110, "upper": True, "per": 3},
    "marker": {"label": "Marker Sweep", "font": "Archivo Black", "size": 118, "base": "FFFFFF", "active": "6BD7FF",
               "strong": "6BD7FF", "outline": 6, "pop": 106, "upper": True, "per": 4},
    "typewriter": {"label": "Typewriter", "font": "Poppins ExtraBold", "size": 88, "base": "F3E9E1", "active": "FFB27A",
                   "strong": "FFB27A", "outline": 4, "pop": 100, "upper": False, "per": 5},
    "underline": {"label": "Underline Animation", "font": "Poppins ExtraBold", "size": 108, "base": "FFFFFF", "active": "FFB27A",
                  "strong": "FFB27A", "outline": 5, "pop": 104, "upper": False, "per": 4},
    "boxed": {"label": "Boxed Captions", "font": "Anton", "size": 126, "base": "FFFFFF", "active": "3C3CFF",
              "strong": "FFFFFF", "outline": 9, "pop": 108, "upper": True, "per": 3},
    "neon": {"label": "Neon Glow", "font": "Anton", "size": 144, "base": "FFFFFF", "active": "FF66FF",
             "strong": "00FFFF", "outline": 10, "pop": 112, "upper": True, "per": 3},
    "podcast": {"label": "Podcast Style", "font": "Poppins ExtraBold", "size": 96, "base": "FFFFFF", "active": "FFB27A",
                "strong": "FFFFFF", "outline": 5, "pop": 104, "upper": False, "per": 5},
    # Additional renderer-backed presets used by the visual caption picker. They reuse the
    # bundled fonts and the same deterministic word-timing engine; no paid font service is required.
    "soft_cut": {"label": "Soft Cut", "font": "Poppins ExtraBold", "size": 106, "base": "FFFFFF", "active": "FFB27A",
                 "strong": "FFB27A", "outline": 4, "pop": 103, "upper": False, "per": 4},
    "beasty": {"label": "Beasty", "font": "Anton", "size": 130, "base": "FFFFFF", "active": "7CE8D6",
               "strong": "7CE8D6", "outline": 6, "pop": 110, "upper": True, "per": 3},
    "think_media": {"label": "Think Media", "font": "Archivo Black", "size": 104, "base": "FFFFFF", "active": "FF66EC",
                     "strong": "FF66EC", "outline": 5, "pop": 108, "upper": True, "per": 3},
    "popline": {"label": "Popline", "font": "Poppins ExtraBold", "size": 110, "base": "FFFFFF", "active": "FFCF33",
                "strong": "FFCF33", "outline": 8, "pop": 110, "upper": True, "per": 3},
    "deep_diver": {"label": "Deep Diver", "font": "Poppins ExtraBold", "size": 96, "base": "D9D9D9", "active": "FFFFFF",
                   "strong": "FFFFFF", "outline": 10, "pop": 103, "upper": False, "per": 4},
    "youshaie": {"label": "Youshaie", "font": "Poppins ExtraBold", "size": 94, "base": "FFFFFF", "active": "7EF7D6",
                 "strong": "7EF7D6", "outline": 3, "pop": 103, "upper": True, "per": 4},
    "pod_p": {"label": "Pod P", "font": "Archivo Black", "size": 100, "base": "FFFFFF", "active": "FF66D2",
              "strong": "FF66D2", "outline": 6, "pop": 106, "upper": True, "per": 4},
    "punch": {"label": "Punch", "font": "Anton", "size": 150, "base": "FFFFFF", "active": "FFD000",
              "strong": "FFD000", "outline": 8, "pop": 116, "upper": True, "per": 2},
    "retro_3d": {"label": "Retro 3D", "font": "Anton", "size": 120, "base": "FFFFFF", "active": "FFC24F",
                 "strong": "FFC24F", "outline": 14, "pop": 110, "upper": True, "per": 3},
    "bouncing_dot": {"label": "Bouncing Dot", "font": "Poppins ExtraBold", "size": 112, "base": "FFFFFF", "active": "FFFFFF",
                     "strong": "FFFFFF", "outline": 8, "pop": 114, "upper": True, "per": 3},
    "breathe": {"label": "Breathe", "font": "Anton", "size": 118, "base": "FFFFFF", "active": "62FF59",
                "strong": "62FF59", "outline": 9, "pop": 108, "upper": True, "per": 3},
    "crossline": {"label": "Crossline", "font": "Poppins ExtraBold", "size": 100, "base": "FFFFFF", "active": "FFB27A",
                   "strong": "FFB27A", "outline": 6, "pop": 103, "upper": False, "per": 4},
    "highlighter": {"label": "Highlighter Box", "font": "Poppins ExtraBold", "size": 108, "base": "211813", "active": "FFFFFF",
                     "strong": "FFFFFF", "outline": 10, "pop": 106, "upper": True, "per": 3, "border_style": 3, "back": "F3C4E7"},
    "sticker": {"label": "Sticker", "font": "Poppins ExtraBold", "size": 104, "base": "211813", "active": "FF6B6B",
                "strong": "211813", "outline": 12, "pop": 106, "upper": False, "per": 4, "border_style": 3, "back": "FFFFFF"},
    "comic": {"label": "Comic", "font": "Anton", "size": 112, "base": "FFFFFF", "active": "FF66D7",
              "strong": "FFFFFF", "outline": 10, "pop": 112, "upper": True, "per": 3},
    "handwritten": {"label": "Handwritten", "font": "Poppins ExtraBold", "size": 94, "base": "FFFFFF", "active": "FFD028",
                     "strong": "FFD028", "outline": 3, "pop": 102, "upper": False, "per": 4, "italic": 1},
}
HOOK = {"font": "Poppins ExtraBold", "size": 96, "ink": "14100E", "box": "FFFFFF", "pad_x": 36, "pad_y": 22, "radius": 26,
        "max_w": 900}
FONT_FILES = {"Poppins ExtraBold": "Poppins-ExtraBold.ttf", "Anton": "Anton-Regular.ttf", "Archivo Black": "ArchivoBlack-Regular.ttf"}
CAP_MAX_W = 960   # captions never run wider than this, whatever is said


class _Font:
    """Measures text exactly as the renderer will draw it, so every word can be placed by hand: the highlighted
    word can grow without pushing its neighbours, and the heading box fits its text."""
    _cache: dict = {}

    def __init__(self, name):
        import struct
        path = Path(__file__).resolve().parent / "fonts" / FONT_FILES.get(name, FONT_FILES["Poppins ExtraBold"])
        d = path.read_bytes()
        tables = {}
        for i in range(struct.unpack(">H", d[4:6])[0]):
            tag, _, off, _ = struct.unpack(">4sIII", d[12 + 16 * i: 28 + 16 * i])
            tables[tag] = off
        self.upm = struct.unpack(">H", d[tables[b"head"] + 18: tables[b"head"] + 20])[0]
        o = tables[b"OS/2"]
        self.asc, self.desc = struct.unpack(">HH", d[o + 74: o + 78])      # what the renderer sizes the font by
        self.cap = struct.unpack(">h", d[o + 88: o + 90])[0] or int(self.upm * 0.7)
        self.path = str(path)
        self._pil = {}

    @classmethod
    def get(cls, name):
        if name not in cls._cache:
            cls._cache[name] = cls(name)
        return cls._cache[name]

    def em(self, size):
        return size * self.upm / (self.asc + self.desc)

    def width(self, text, size):
        """Pixels wide at this ASS size."""
        try:
            from PIL import ImageFont
            if "f" not in self._pil:
                self._pil["f"] = ImageFont.truetype(self.path, 200)
            return self._pil["f"].getlength(text) * self.em(size) / 200
        except Exception:  # noqa: BLE001 - no measuring library: a fair estimate keeps clips rendering
            return len(text) * self.em(size) * 0.62

    def cap_shift(self, size):
        """How far below the anchor the middle of a capital letter sits when text is centred on a point."""
        return ((self.asc - self.desc) / 2 - self.cap / 2) * size / (self.asc + self.desc)


CAPTION_LEAD = 0.0  # measured: word stamps are within 0.15 s of the voice, so no shift is needed
def install_fonts():
    """Copy the bundled caption fonts next to the data, so captions look the same on every machine and server."""
    src = Path(__file__).resolve().parent / "fonts"
    for f in src.glob("*.ttf"):
        if not (config.FONTS_DIR / f.name).exists():
            shutil.copyfile(f, config.FONTS_DIR / f.name)


LAYOUTS = {"blur": "Blurred fill", "zoom": "Zoomed in", "crop": "Fill screen"}
OUTPUT_ASPECTS = {"vertical": (1080, 1920), "landscape": (1920, 1080), "square": (1080, 1080), "portrait": (1080, 1350)}


def _ts(t):
    t = max(0.0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def _clean(text):
    return re.sub(r"[\x00-\x1f\x7f]+", " ", re.sub(r"[{}\\]", "", str(text))).strip()


def _key(word):
    return re.sub(r"[^a-z0-9']", "", word.lower())


def _groups(words, per):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= per or sum(len(x["w"]) for x in cur) + len(w["w"]) > 16
                    or w["s"] - cur[-1]["e"] > 0.45 or cur[-1]["w"][-1:] in ".?!"):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def geometry(src_w, src_h, layout, out_w=W, out_h=H):
    """Return layout geometry for Blurred fill, Zoomed in, and Fill screen.

    ``blur`` is Blurred fill: the complete source sits across the width with blurred top/bottom.
    ``zoom`` is Zoomed in: a closer subject crop covering ~72% height with subtle edge blur.
    ``crop`` is Fill screen: the source fills the full 9:16 Shorts frame (100% height).
    """
    source_h = out_w * src_h / max(1, src_w)
    if layout in ("crop", "fill", "full"):
        fg_h = out_h
    elif layout == "zoom":
        fg_h = min(out_h, int(round(out_h * 0.72 / 2)) * 2)
    else:
        fg_h = min(out_h, int(round(source_h / 2)) * 2)
    top = (out_h - fg_h) // 2
    unit = out_h / H
    if layout in ("crop", "fill", "full"):
        return layout, fg_h, int(300 * unit), int(1380 * unit)
    return layout, fg_h, max(int(230 * unit), int(top - 190 * unit)), min(int(1640 * unit), int(top + fg_h + 180 * unit))


def _hook_events(hook, dur, y, canvas_w=W):
    """The heading: dark text in a white rounded box that fits it, on one line or two balanced ones."""
    f, size = _Font.get(HOOK["font"]), HOOK["size"]
    words = hook.split()
    if not words:
        return []
    lines = [" ".join(words)]
    if f.width(lines[0], size) > HOOK["max_w"] and len(words) > 1:      # two lines, split where they come out most even
        cut = min(range(1, len(words)), key=lambda i: max(f.width(" ".join(words[:i]), size), f.width(" ".join(words[i:]), size)))
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    widest = max(f.width(l, size) for l in lines)
    if widest > HOOK["max_w"]:
        size = max(40, int(size * HOOK["max_w"] / widest))
        widest = max(f.width(l, size) for l in lines)
    line_h = f.em(size) * 1.16
    bw, bh = widest + 2 * HOOK["pad_x"], line_h * len(lines) + 2 * HOOK["pad_y"]
    x0, y0, r = (canvas_w - bw) / 2, y - bh / 2, min(HOOK["radius"], bh / 2)
    x1, y1 = x0 + bw, y0 + bh
    n = lambda v: f"{v:.0f}"                                                         # noqa: E731
    box = (f"m {n(x0 + r)} {n(y0)} l {n(x1 - r)} {n(y0)} b {n(x1)} {n(y0)} {n(x1)} {n(y0)} {n(x1)} {n(y0 + r)} "
           f"l {n(x1)} {n(y1 - r)} b {n(x1)} {n(y1)} {n(x1)} {n(y1)} {n(x1 - r)} {n(y1)} "
           f"l {n(x0 + r)} {n(y1)} b {n(x0)} {n(y1)} {n(x0)} {n(y1)} {n(x0)} {n(y1 - r)} "
           f"l {n(x0)} {n(y0 + r)} b {n(x0)} {n(y0)} {n(x0)} {n(y0)} {n(x0 + r)} {n(y0)}")
    span = f"{_ts(0)},{_ts(dur)}"
    ev = [f"Dialogue: 3,{span},Hook,,0,0,0,,{{\\an7\\pos(0,0)\\fad(160,0)\\c&H{HOOK['box']}&\\p1}}{box}{{\\p0}}"]
    for i, line in enumerate(lines):
        cy = y - line_h * (len(lines) - 1) / 2 + i * line_h - f.cap_shift(size)
        ev.append(f"Dialogue: 4,{span},Hook,,0,0,0,,{{\\an5\\pos({canvas_w // 2},{cy:.0f})\\fad(160,0)\\fs{size}}}{line}")
    return ev


def _emoji_for(clip) -> str:
    """A small, deterministic emoji layer. It uses the transcript/category, not a paid image model."""
    text = " ".join(str(clip.get(k) or "") for k in ("category", "hook", "title", "description")).lower()
    for terms, emoji in ((
        (("laugh", "funny", "comedy", "joke"), "😂"),
        (("shock", "surpris", "insane", "unbeliev", "crazy"), "😱"),
        (("sad", "cry", "emotional", "heart"), "🥲"),
        (("love", "cute", "romance"), "😍"),
        (("angry", "rage", "fight"), "😤"),
        (("gaming", "game", "win", "loss"), "🎮"),
        (("food", "eat", "recipe", "cook"), "🍽️"),
        (("travel", "trip", "mountain", "hike"), "🌍"),
        (("tip", "learn", "how to", "advice"), "💡"),
    )):
        if any(t in text for t in terms):
            return emoji
    return "🔥"


def build_ass(words, start, end, hook, style_name, highlight, hook_y, cap_y, emoji=False, captions=True,
              clip=None, canvas_w=W, canvas_h=H) -> str:
    st = STYLES.get(style_name, STYLES["bounce"])
    words = [dict(w, s=w["s"] - CAPTION_LEAD, e=w["e"] - CAPTION_LEAD) for w in words]
    strong = {_key(h) for h in highlight if _key(h)}
    border_style = int(st.get("border_style", 1) or 1)
    back = st.get("back", "000000")
    italic = int(st.get("italic", 0) or 0)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {canvas_w}
PlayResY: {canvas_h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['font']},{st['size']},&H00{st['base']},&H00{st['base']},&H00000000,&H00{back},0,{italic},0,0,100,100,0,0,{border_style},{st['outline']},0,5,0,0,0,1
Style: Hook,{HOOK['font']},{HOOK['size']},&H00{HOOK['ink']},&H00{HOOK['ink']},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dur = end - start
    ev = _hook_events(_clean(hook), dur, hook_y, canvas_w) if captions else []
    f = _Font.get(st["font"])
    inside = [dict(w, w=_clean(w["w"])) for w in words if w["s"] >= start - 0.05 and w["s"] < end]
    inside = sorted((w for w in inside if w["w"]), key=lambda w: w["s"])
    for i, w in enumerate(inside[:-1]):
        w["e"] = max(w["s"], min(w["e"], inside[i + 1]["s"]))
    groups = _groups(inside, st["per"]) if captions else []
    for gi, g in enumerate(groups):
        g_start = max(0.0, g[0]["s"] - start)
        g_end = min(g[-1]["e"] + 0.25, groups[gi + 1][0]["s"] if gi + 1 < len(groups) else end) - start
        if g_end - g_start < 0.02:
            continue
        texts = []
        for x in g:
            t = re.sub(r"[.,;:]+$", "", x["w"])
            texts.append(t.upper() if st["upper"] else t)
        if not all(roman.drawable(t) for t in texts):
            # A script the caption font cannot draw (Japanese, Thai, Chinese...): its words cannot be measured, so
            # they are not placed one by one. The line is drawn whole and centred, in a font the system has for it.
            line = " ".join(texts)
            fs = max(44, min(int(st["size"] * 0.7), int(1500 / max(1, len(line)) * 1.6)))
            ev.append(f"Dialogue: 1,{_ts(g_start)},{_ts(g_end)},Cap,,60,60,0,,{{\\an5\\pos({canvas_w // 2},{cap_y:.0f})\\q0\\fs{fs}}}{line}")
            continue
        size = st["size"]
        gap = f.width("n n", size) - 2 * f.width("n", size) + (2 * st["outline"] + 6) * size / st["size"]   # a space, plus room for both outlines
        total = sum(f.width(t, size) for t in texts) + gap * (len(texts) - 1)
        if total > CAP_MAX_W:                                  # a long phrase: shrink it to fit, never run off the frame
            size = max(36, int(size * CAP_MAX_W / total))
            gap = f.width("n n", size) - 2 * f.width("n", size) + (2 * st["outline"] + 6) * size / st["size"]   # a space, plus room for both outlines
            total = sum(f.width(t, size) for t in texts) + gap * (len(texts) - 1)
        cy = cap_y - f.cap_shift(size)
        x = (canvas_w - total) / 2
        p = st["pop"]
        for i, (w, t) in enumerate(zip(g, texts)):
            wd = f.width(t, size)
            p = max(104, min(st["pop"], 100 + int(2200 / max(wd, 1))))   # long words grow less, so they never touch their neighbours
            pos = f"\\an5\\pos({x + wd / 2:.0f},{cy:.0f})\\fs{size}"
            x += wd + gap
            a = max(g_start, w["s"] - start)
            b = (g[i + 1]["s"] - start) if i + 1 < len(g) else g_end
            base = st["strong"] if _key(w["w"]) in strong else st["base"]
            if a - g_start >= 0.02:                                                   # waiting to be said
                ev.append(f"Dialogue: 1,{_ts(g_start)},{_ts(a)},Cap,,0,0,0,,{{{pos}\\c&H{base}&}}{t}")
            if b - a >= 0.02:                                                         # being said: colour and a quick pop, in front
                ev.append(f"Dialogue: 2,{_ts(a)},{_ts(b)},Cap,,0,0,0,,{{{pos}\\c&H{st['active']}&\\fscx94\\fscy94"
                          f"\\t(0,90,\\fscx{p}\\fscy{p})\\t(90,200,\\fscx{p - 5}\\fscy{p - 5})}}{t}")
            if g_end - b >= 0.02:                                                     # said
                ev.append(f"Dialogue: 1,{_ts(b)},{_ts(g_end)},Cap,,0,0,0,,{{{pos}\\c&H{base}&\\fscx{p - 5}\\fscy{p - 5}"
                          f"\\t(0,90,\\fscx100\\fscy100)}}{t}")
    if emoji:
        icon = _emoji_for(clip or {})
        preset = (clip or {}).get("emoji_preset", "balanced")
        size = {"subtle": 48, "balanced": 68, "expressive": 88, "gaming": 96}.get(preset, 68)
        frequency = max(1, min(5, int((clip or {}).get("emoji_frequency", 3) or 3)))
        count = max(1, min(8, round(max(1.0, dur) / max(1.0, 9.0 / frequency))))
        for i in range(count):
            a = dur * i / count
            b = min(dur, a + min(1.8, dur / count))
            span = f"{_ts(a)},{_ts(b)}"
            ev.append(f"Dialogue: 6,{span},Hook,,0,0,0,,{{\\an7\\pos({canvas_w - int(102 * canvas_w / W)},{int(180 * canvas_h / H)})\\fnSegoe UI Emoji\\fs{size}}}{icon}")
    return head + "\n".join(ev) + "\n"


def _filter(layout, fg_h, effects=None, out_w=W, out_h=H):
    effects = effects or {}
    preset = effects.get("color_preset", "original")
    preset_values = {"natural": (0.02, 1.06, 1.08), "vibrant": (0.0, 1.1, 1.28),
                     "warm": (0.02, 1.04, 1.08), "cool": (0.0, 1.04, 0.98), "original": (0.0, 1.0, 1.0)}
    bright, contrast, saturation = preset_values.get(preset, preset_values["original"])
    bright += float(effects.get("color_brightness", 0) or 0) / 100
    contrast *= float(effects.get("color_contrast", 100) or 100) / 100
    saturation *= float(effects.get("color_saturation", 100) or 100) / 100
    sharpness = max(0.0, min(1.5, float(effects.get("color_sharpness", 0) or 0) / 66.67))
    color = f",eq=brightness={bright:.3f}:contrast={contrast:.3f}:saturation={saturation:.3f}" if (
        effects.get("color_correct") and (preset != "original" or bright or contrast != 1.0 or saturation != 1.0)) else ""
    sharp = f",unsharp=5:5:{sharpness:.2f}:5:5:{sharpness:.2f}" if effects.get("color_correct") and sharpness else ""
    zoom_scale = {"gentle": 1.04, "punch": 1.10, "cinematic": 1.06}.get(effects.get("zoom_preset"), 1.08)
    zoom = bool(effects.get("auto_zoom")) and zoom_scale > 1
    fg_w, fg_h_in = (int(out_w * zoom_scale), int(fg_h * zoom_scale)) if zoom else (out_w, fg_h)
    crop_fg = f"scale={fg_w}:{fg_h_in}:force_original_aspect_ratio=increase,crop={out_w}:{fg_h}"
    if layout in ("crop", "fill", "full"):
        w, h = (int(out_w * zoom_scale), int(out_h * zoom_scale)) if zoom else (out_w, out_h)
        return f"[0:v]fps={config.OUT_FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h}{color}{sharp},setsar=1[v0];"

    if layout == "zoom":
        fit_fg = f"scale={out_w}:{fg_h}:force_original_aspect_ratio=increase,crop={out_w}:{fg_h}{color}{sharp}"
    else:
        fit_fg = f"scale={out_w}:{fg_h}:force_original_aspect_ratio=decrease,pad={out_w}:{fg_h}:(ow-iw)/2:(oh-ih)/2:color=0x0B0E17{color}{sharp}"

    return (f"[0:v]fps={config.OUT_FPS},split=2[a][b];"
            f"[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=6:2,"
            f"scale={out_w}:{out_h},eq=brightness=-0.14:saturation=1.15{color}[bg];"
            f"[b]{fit_fg}[fg];"
            f"[bg][fg]overlay=0:(H-h)/2,setsar=1[v0];")


_qsv_ok = None
RENDER_SECONDS = 600      # one clip's video encode; far beyond normal, so a frozen encoder is stopped, not waited on


def _has_audio_track(src: Path) -> bool:
    """Check if the source media contains an audio stream."""
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)],
            capture_output=True, text=True, timeout=10
        )
        return "audio" in (res.stdout or "").lower()
    except Exception:
        return True


def _audio_filters(effects):
    filters = []
    if effects.get("speech_cleanup"):
        # Clamp between -80 and -20: -18 causes FFmpeg afftdn parameter 'nf' out of range [-80 - -20]
        noise = {"basic": -25, "strong": -20}.get(effects.get("cleanup_level", "basic"), -25)
        try:
            noise = max(-80, min(-20, int(noise)))
        except (ValueError, TypeError):
            noise = -25
        filters += ["highpass=f=70", "lowpass=f=15000", f"afftdn=nf={noise}"]
    if effects.get("audio_enhance"):
        filters.append("acompressor=threshold=-18dB:ratio=2:attack=20:release=250:makeup=2")
    filters.append("loudnorm=I=-14:TP=-1.5:LRA=11")
    return ",".join(filters)


def _write_sfx(work: Path, clip: dict) -> Path:
    """Make a tiny neutral accent locally, so Auto SFX works without an external sound API or asset download."""
    text = " ".join(str(clip.get(k) or "") for k in ("category", "hook", "title")).lower()
    freqs = (520, 780) if any(x in text for x in ("shock", "insane", "surpris")) else (440, 660)
    rate, seconds = 48000, 0.22
    out = work / "auto-sfx.wav"
    with wave.open(str(out), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        frames = bytearray()
        for i in range(int(rate * seconds)):
            t = i / rate
            env = math.exp(-10 * t)
            value = 0.16 * env * (math.sin(2 * math.pi * freqs[0] * t) + 0.45 * math.sin(2 * math.pi * freqs[1] * t))
            frames.extend(struct.pack("<h", max(-32767, min(32767, int(value * 32767)))))
        f.writeframes(frames)
    return out


def render_clip(src: Path, out_dir: Path, name: str, clip: dict, words: list, src_w: int, src_h: int,
                cancel=None, output_aspect="vertical") -> dict:
    """Writes <name>.mp4, <name>.jpg and <name>.ass into out_dir. Returns file names."""
    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = clip["start"], clip["end"]
    effects = clip or {}
    out_w, out_h = OUTPUT_ASPECTS.get(output_aspect, OUTPUT_ASPECTS["vertical"])
    layout, fg_h, hook_y, cap_y = geometry(src_w, src_h, clip.get("layout", "blur"), out_w, out_h)
    ass = build_ass(words, start, end, clip.get("hook", ""), clip.get("style", "bounce"),
                    clip.get("highlight_words", []), hook_y, cap_y, bool(effects.get("emoji")),
                    bool(effects.get("captions", True)), clip, out_w, out_h)
    # The clip is made in a short work folder and moved into place afterwards. The caption step of ffmpeg cannot
    # open files whose full path is longer than 260 characters on Windows, which a data folder deep inside other
    # folders easily reaches. Inside the work folder every name is short and relative (a drive colon would also
    # break the filter syntax).
    work = Path(tempfile.mkdtemp(prefix="pk"))
    try:
        return _render_in(work, src, out_dir, name, start, end, layout, fg_h, ass, cancel, effects, out_w, out_h)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _render_in(work: Path, src: Path, out_dir: Path, name: str, start, end, layout, fg_h, ass: str,
               cancel=None, effects=None, out_w=W, out_h=H) -> dict:
    global _qsv_ok
    effects = effects or {}
    (work / f"{name}.ass").write_text(ass, encoding="utf-8")
    (work / "f").mkdir()
    for f in config.FONTS_DIR.glob("*.ttf"):
        shutil.copyfile(f, work / "f" / f.name)
    fc = _filter(layout, fg_h, effects, out_w, out_h)
    video_in = "v0"
    dur = max(0.1, end - start)
    transition = effects.get("transition", "fade") if effects.get("auto_transition") else "none"
    if transition != "none":
        fade_end = max(0.02, dur - 0.18)
        color = "black" if transition == "dip_black" else "white" if transition == "flash" else None
        suffix = f":color={color}" if color else ""
        fade_in = f"fade=t=in:st=0:d=0.18{suffix}"
        fade_out = f"fade=t=out:st={fade_end:.2f}:d=0.18{suffix}"
        fc += f"[v0]{fade_in},{fade_out}[v1];"
        video_in = "v1"
    if effects.get("captions", True) or effects.get("emoji"):
        fc += f"[{video_in}]ass={name}.ass:fontsdir=f[v]"
    else:
        fc += f"[{video_in}]null[v]"
    src = Path(src).resolve()
    has_audio = _has_audio_track(src)
    audio = _audio_filters(effects)
    base = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(src)]
    if has_audio:
        if effects.get("auto_sfx"):
            sfx = _write_sfx(work, effects)
            fc += (f";[0:a:0]{audio}[maina];"
                   f"[1:a:0]adelay=delays=80:all=1,volume=0.8,apad,atrim=duration={dur:.2f}[sfx];"
                   f"[maina][sfx]amix=inputs=2:duration=first:dropout_transition=0:weights=1 0.18[a]")
            base += ["-i", str(sfx), "-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
        else:
            base += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a:0", "-af", audio]
    else:
        if effects.get("auto_sfx"):
            sfx = _write_sfx(work, effects)
            fc += (f";[1:a:0]adelay=delays=80:all=1,volume=0.8,apad,atrim=duration={dur:.2f}[sfx];"
                   f"[sfx]{audio}[a]")
            base += ["-i", str(sfx), "-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
        else:
            base += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                     "-filter_complex", fc, "-map", "[v]", "-map", "1:a:0"]
    base += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-pix_fmt"]
    encoders = []
    if _qsv_ok is not False:
        encoders.append(("qsv", ["nv12", "-c:v", "h264_qsv", "-global_quality", "23", "-preset", "fast"]))
    encoders.append(("x264", ["yuv420p", "-c:v", "libx264", "-crf", "21", "-preset", "veryfast"]))
    err = None
    for label, enc in encoders:
        try:
            run(base + enc + [f"{name}.mp4"], cwd=work, timeout=RENDER_SECONDS, cancel=cancel)
            if label == "qsv":
                _qsv_ok = True
            break
        except RuntimeError as e:
            if cancel is not None and cancel.is_set():
                raise
            err = str(e)[-1200:]
        if label == "qsv":
            _qsv_ok = False
    else:
        raise RuntimeError(f"Render failed: {err}")
    cover_t = min(1.2, (end - start) / 2)
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{cover_t:.2f}", "-i", f"{name}.mp4", "-frames:v", "1",
         "-q:v", "3", f"{name}.jpg"], cwd=work, cancel=cancel)
    for ext in ("mp4", "jpg", "ass"):
        shutil.move(str(work / f"{name}.{ext}"), str(out_dir / f"{name}.{ext}"))
    return {"file": f"{name}.mp4", "cover": f"{name}.jpg", "layout": layout}
