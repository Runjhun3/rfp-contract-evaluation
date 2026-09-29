"""Criteria that give marks by HOW MANY qualifying items the bidder shows ("up to 3
projects: 5 marks, 4-6: 7, 7 or more: 10"). The bands are the approved criteria's
data; this only looks one up. Mirrored in the final_score view (migration 009).
"""
from decimal import Decimal

from app.schemas.records import CountBand


def band_marks(bands: list[CountBand], count: int) -> Decimal:
    """The marks of the band the count falls in (the highest band that starts at or
    below it); 0 when it falls in none."""
    fitting = [b for b in bands if count >= b.min and (b.max is None or count <= b.max)]
    return max(fitting, key=lambda b: b.min).marks if fitting else Decimal(0)


def describe(bands: list[CountBand]) -> str:
    """"1-3 items: 5 marks; 4-6: 7; 7 or more: 10" for the rule text and summaries."""
    parts = [f"{b.min}{'-' + str(b.max) if b.max is not None else ' or more'}: "
             f"{format(b.marks.normalize(), 'f')}" for b in sorted(bands, key=lambda b: b.min)]
    return "; ".join(parts)
