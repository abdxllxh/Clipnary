"""Deterministic tests for highlight quality without a network call or a real video file."""
import os
import shutil
import sys
import tempfile

import numpy as np

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-highlights-")
os.environ["DATABASE_URL"] = ""
sys.path.insert(0, ".")
from studio import brain  # noqa: E402

fails = []


def check(name, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(name)


def speech(start, sentences):
    """Create word timestamps with punctuation and realistic gaps."""
    out, t = [], float(start)
    for sentence in sentences:
        parts = sentence.split()
        for i, word in enumerate(parts):
            out.append({"w": word + ("!" if i == len(parts) - 1 and sentence.endswith("!") else
                                     "?" if i == len(parts) - 1 and sentence.endswith("?") else
                                     "." if i == len(parts) - 1 else ""),
                        "s": round(t, 2), "e": round(t + 0.42, 2)})
            t += 0.55
        t += 0.85
    return out


generic = speech(8, [
    "Today guys we are talking about the video and basically going through the settings",
    "This part is just a normal explanation of the thing and the channel",
])
interesting = speech(60, [
    "Wait wait what was that",
    "He missed the final shot and then somehow won the game",
    "Everyone in chat is screaming right now",
    "I cannot believe that actually happened right now",
])
repeat = speech(95, [
    "Wait wait what was that",
    "He missed the final shot and then somehow won the game",
    "Everyone in chat is screaming right now",
    "I cannot believe that actually happened right now",
])
words = generic + interesting + repeat
db = np.zeros(135, dtype=np.float32)
db[16:19] = 8.0                         # loud but generic: a deliberate false positive
db[64:67] = 6.0                         # loud and semantically exciting
db[99:102] = 6.0                        # duplicate exciting moment


def ai_candidates(_prompt, schema=None, purpose=""):
    return [
        {"start": 10, "end": 27, "score": 86, "category": "other", "hook": "NORMAL TALK", "title": "Generic",
         "description": "", "hashtags": [], "highlight_words": [], "reason": "A smooth paragraph."},
        {"start": 60, "end": 80, "score": 78, "category": "shock", "hook": "WHAT JUST HAPPENED", "title": "Reaction",
         "description": "", "hashtags": [], "highlight_words": [], "reason": "A surprising reaction."},
        {"start": 95, "end": 115, "score": 77, "category": "shock", "hook": "SAME MOMENT", "title": "Repeated reaction",
         "description": "", "hashtags": [], "highlight_words": [], "reason": "The same reaction again."},
    ], "fixture-model", 12


# ---- AI results are reranked with available signals and the user preference reaches the prompt safely
prompts = []
brain.ask_ai = lambda prompt, schema=None, purpose="": (prompts.append(prompt), ai_candidates(prompt, schema, purpose))[1]
ai_clips, ai_info = brain.find_clips(words, db, 135, title="fixture", max_clips=2, min_len=18, max_len=35,
                                     preferences="find the football reaction", speech_language="hi", genre="reaction")
best_ai = max(ai_clips, key=lambda c: c["score"], default={})
check("AI ranking prefers the exciting reaction over generic talk", 55 <= best_ai.get("start", -1) < 90)
check("generic model candidates are rejected instead of padding the grid", len(ai_clips), 1)
check("the repeated moment does not consume another result", not any(c["start"] >= 90 for c in ai_clips))
check("user preference is included as a ranking hint", prompts and "football reaction" in prompts[0])
check("language and genre reach the AI prompt", prompts and "hi" in prompts[0] and "reaction" in prompts[0])
check("selected clips include ranking evidence", ai_clips and all("evidence" in c for c in ai_clips))
check("AI selection reports lightweight telemetry", set(("candidates", "ranked", "accepted", "duration_ms")) <= set(ai_info["selection"]))

# The model deliberately ends in the middle of a sentence. The boundary should land on the completed sentence.
ends = brain.sentence_ends(interesting)
check("AI result ends at a natural sentence boundary", best_ai and any(x <= best_ai["end"] <= x + 0.36 for x in ends))

# ---- no AI: deterministic fallback uses transcript context and audio changes, not loudness alone
def no_ai(*args, **kwargs):
    raise RuntimeError("no AI in this fixture")


brain.ask_ai = no_ai
fallback, fallback_info = brain.find_clips(words, db, 135, max_clips=1, min_len=18, max_len=35)
check("fallback returns a clip", len(fallback), 1)
check("fallback chooses the exciting moment over a loud generic paragraph",
      fallback and fallback[0]["start"] < 60 and fallback[0]["end"] >= 74)
check("fallback is explicitly multi-signal", "deterministic" in fallback_info["note"].lower())
check("fallback reports its mode", fallback_info["selection"]["fallback"], True)
check("fallback uses transcript-derived hook and summary", fallback and fallback[0]["hook"] != "STORY" and bool(fallback[0]["description"]))
check("fallback never pads with a generic story moment", not any(c["title"] == "Story moment" for c in fallback))

# A direct signal comparison makes the loudness-only regression visible even if a future fixture changes its order.
lines = brain.make_lines(words, brain.loud_zscore(db))
generic_q = brain._candidate_quality(8, 38, words, lines, brain.loud_zscore(db), 18, 35)
interesting_q = brain._candidate_quality(60, 90, words, lines, brain.loud_zscore(db), 18, 35)
check("interesting signal score beats loud generic signal", interesting_q["score"] > generic_q["score"])
check("loud generic signal is marked generic", generic_q["generic"] > 0)

# Existing clips remain a hard exclusion for Find More, while a separate moment survives.
brain.ask_ai = lambda *args, **kwargs: ([
    {"start": 60, "end": 80, "score": 95, "category": "shock", "hook": "OLD", "title": "Old",
     "description": "", "hashtags": [], "highlight_words": [], "reason": "Already shown."},
    {"start": 10, "end": 27, "score": 60, "category": "story", "hook": "NEW", "title": "New",
     "description": "", "hashtags": [], "highlight_words": [], "reason": "Another moment."},
], "fixture-model", 4)
more, _ = brain.find_clips(words, db, 135, max_clips=2, min_len=18, max_len=35,
                           existing=[{"start": 64, "end": 76}])
check("existing clip range is excluded from another search", not any(c["start"] < 80 and c["end"] > 60 for c in more))

print("ALL PASSED" if not fails else f"{len(fails)} failed")
shutil.rmtree(os.environ["PEAKCUT_DATA"], ignore_errors=True)
sys.exit(1 if fails else 0)
