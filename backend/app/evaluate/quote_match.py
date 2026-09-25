"""Is a quote on a page? Exact after normalising, else a fuzzy partial match
(standard library difflib) that tolerates OCR noise. Score 0-100.
"""
import re
from difflib import SequenceMatcher

_SPACE = re.compile(r"\s+")
_NOISE = re.compile(r"[|`'\"“”‘’]")


def normalise(text: str) -> str:
    return _SPACE.sub(" ", _NOISE.sub("", text.lower())).strip()


def quote_score(quote: str, page_text: str) -> int:
    needle, hay = normalise(quote), normalise(page_text)
    if not needle:
        return 0
    if needle in hay:
        return 100
    return round(_partial_ratio(needle, hay) * 100)


def _partial_ratio(needle: str, hay: str) -> float:
    if len(needle) > len(hay):
        return SequenceMatcher(None, needle, hay, autojunk=False).ratio()
    best = 0.0
    blocks = SequenceMatcher(None, needle, hay, autojunk=False).get_matching_blocks()
    for block in blocks:
        start = max(0, block.b - block.a)
        window = hay[start:start + len(needle)]
        best = max(best, SequenceMatcher(None, needle, window, autojunk=False).ratio())
        if best >= 0.995:
            break
    return best
