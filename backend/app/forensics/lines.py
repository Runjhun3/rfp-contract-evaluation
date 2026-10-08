"""Reading lines and runs of words, and the straight lines fitted through them, for the
word-position and pixel checks (D-058, D-061)."""
import math
from statistics import median

from app.schemas.records import Word

MIN_LINE = 4
GAP = 2.0                # a gap this many word heights wide ends a run (a table column)


def group_lines(words: list[Word]) -> list[list[Word]]:
    """Words in reading lines: a word joins a line when its middle is within 0.7 of a
    word height of the line's middle (lines are further apart), so a figure pasted a
    little off its line stays in it to be compared; each line left to right."""
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: w.y + w.h / 2):
        middle = word.y + word.h / 2
        line = lines[-1] if lines else None
        if line and abs(middle - median(w.y + w.h / 2 for w in line)) < \
                0.7 * median(w.h for w in line):
            line.append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w.x) for line in lines]


def runs(line: list[Word]) -> list[list[Word]]:
    """A line split at each gap wider than GAP word heights: its cells or columns."""
    found, height = [[line[0]]], median(w.h for w in line)
    for left, right in zip(line, line[1:]):
        (found.append([right]) if right.x - (left.x + left.w) > GAP * height
         else found[-1].append(right))
    return found


def fit(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """The least-squares straight line through (x, y) points: its slope and the point
    (x, y) it passes through at their middle."""
    mx = sum(x for x, _ in points) / len(points)
    my = sum(y for _, y in points) / len(points)
    spread = sum((x - mx) ** 2 for x, _ in points) or 1e-9
    return sum((x - mx) * (y - my) for x, y in points) / spread, mx, my


def baseline_at(tall: list[Word], line: list[Word], x: float) -> float:
    """Where the tall words' bottoms run at x, along the slant of the line (a slanted
    scan's line slants, not its words). The slant is fitted through every word of the
    line, so a few tall words at one end cannot tilt it."""
    slope = fit([(w.x + w.w / 2, w.y + w.h / 2) for w in line])[0]
    return slope * x + median(w.y + w.h - slope * (w.x + w.w / 2) for w in tall)


def angle(line: list[Word]) -> float:
    """The line's slope in degrees, from its words' middles."""
    return math.degrees(math.atan(fit([(w.x + w.w / 2, w.y + w.h / 2) for w in line])[0]))


def page_tilt(lines: list[list[Word]]) -> float | None:
    angles = [angle(line) for line in lines if len(line) >= MIN_LINE + 1]
    return median(angles) if len(angles) >= 3 else None
