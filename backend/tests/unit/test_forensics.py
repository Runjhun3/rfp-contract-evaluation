"""Stamps, signatures, layout and pixels on synthetic images only (no sample bid)."""
import cv2
import numpy as np

from app.forensics.images import Scan, in_scan, inside
from app.forensics.layout import missing_pages, near_copy, odd_pages
from app.forensics.marks import find_marks
from app.forensics.pixels import pixel_findings
from app.forensics.stamps import norm, reused
from app.schemas.records import Word

BLUE = (180, 60, 40)          # BGR ink
BOX = {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}


def scan(draw) -> Scan:
    pixels = np.full((1000, 700, 3), 255, np.uint8)
    draw(pixels)
    return Scan(pixels=pixels, box=BOX, jpeg=False, dpi=200)


def stamp(pixels, centre=(500, 800), angle=0):
    cv2.circle(pixels, centre, 60, BLUE, 4)
    cv2.circle(pixels, centre, 42, BLUE, 2)
    cv2.putText(pixels, "OFFICE", (centre[0] - 38, centre[1] + 6), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, BLUE, 2)
    if angle:                 # stamped again: the impression lands turned
        turn = cv2.getRotationMatrix2D(centre, angle, 1.0)
        pixels[:] = cv2.warpAffine(pixels, turn, (700, 1000), borderValue=(255, 255, 255))


def word(text, x, y, w=0.05, h=0.012):
    return Word(text=text, x=x, y=y, w=w, h=h)


def test_a_round_ink_stamp_is_found_a_frame_or_a_paragraph_is_not():
    assert [m.kind for m in find_marks(scan(stamp), [])] == ["STAMP"]
    frame = scan(lambda p: cv2.rectangle(p, (100, 400), (600, 470), (40, 40, 220), 3))
    assert find_marks(frame, []) == []
    # Lines of text running through the stamp's box: a paragraph, not a stamp.
    through = [word(f"w{i}", 0.5 + 0.06 * (i % 6), 0.66 + 0.02 * (i // 6), w=0.1)
               for i in range(12)]
    assert find_marks(scan(stamp), through) == []


def test_the_same_stamp_image_on_another_page_is_flagged_but_not_the_bidders_own():
    marks = {n: [(m, BOX) for m in find_marks(scan(s), [])]
             for n, s in ((3, stamp), (7, stamp), (9, lambda p: stamp(p, angle=9)))}
    page, other = (np.random.default_rng(i).integers(0, 255, (64, 64)).astype(np.float32)
                   for i in (1, 2))
    thumbs = {3: page, 7: other, 9: page}
    found = reused(7, marks, thumbs, own=[])
    assert [(f.kind, f.page) for f in found] == [("STAMP_REUSED", 7)]
    assert "same image as on p.3" in found[0].note
    assert reused(9, marks, thumbs, own=[]) == []          # stamped again: not alike
    assert reused(7, marks, {**thumbs, 7: page}, own=[]) == []   # one scan shown twice
    assert reused(7, marks, thumbs, own=[norm(marks[3][0][0].crop)]) == []


def text(words, figures):
    return [word(t, 0.05 + 0.06 * (i % 12), 0.2 + 0.02 * (i // 12))
            for i, t in enumerate(words + figures)]


BODY = [f"term{i}" for i in range(45)]


def test_a_letter_reused_with_other_dates_is_flagged_but_not_ocr_noise_or_a_series():
    figures = ["12.05.2021", "Rs.1,50,000", "31.03.2022"]
    scanned = {4: text(BODY, figures), 9: text(BODY, ["12.05.2023", *figures[1:]])}
    found = near_copy(9, scanned, lambda a, b: False)
    assert found.kind == "NEAR_COPY" and "12.05.2021, 12.05.2023" in found.note
    assert near_copy(9, scanned, lambda a, b: True) is None    # one scan shown twice
    misread = {**scanned, 9: text(BODY, ["12.05.2021", "Rs.1,50,000co", "31.03.2O22"])}
    assert near_copy(9, misread, lambda a, b: False) is None
    series = {4: text(BODY, ["M2410207"]), 9: text(BODY, ["M2500480"])}
    assert near_copy(9, series, lambda a, b: False) is None


def test_only_a_gap_inside_a_documents_numbered_pages_is_flagged():
    texts = {10: "Page 1 of 4", 11: "Page 2 of 4", 12: "Page 4 of 4",
             20: "Page 2 of 3", 21: "Page 3 of 3"}
    found = missing_pages(11, texts)
    assert found.kind == "PAGE_MISSING" and "pages 1, 2, 4 but not 3" in found.note
    assert missing_pages(21, texts) is None      # an unnumbered first page is no gap


def test_the_letterhead_is_read_from_the_scan_and_an_odd_page_stands_out():
    head = [word(t, 0.1 + 0.1 * i, 0.03) for i, t in enumerate(["national", "sports", "office"])]
    page = head + text(BODY, ["12.05.2021"])
    shifted = [w.model_copy(update={"x": w.x + 0.12}) for w in page]
    scanned = {1: page, 2: page, 3: page, 4: shifted}
    found = odd_pages([1, 2, 3, 4], scanned)
    assert [f.page for f in found] == [4]


def test_only_the_words_inside_a_scan_count_and_are_placed_within_it():
    caption = word("(2/5)", 0.5, 0.05)
    within = word("12.05.2021", 0.5, 0.5)
    assert inside(BOX, [caption, within]) == [within]
    placed = in_scan(BOX, [caption, within])[0]
    assert (round(placed.x, 4), round(placed.y, 4)) == (0.5, 0.5)


def test_a_copied_patch_is_found_outside_the_text_and_a_caption_is_never_measured():
    def draw(p):
        patch = np.random.default_rng(7).integers(0, 255, (120, 120, 3), dtype=np.uint8)
        p[600:720, 100:220] = patch
        p[600:720, 450:570] = patch
    text_place = [word("Dated", 0.15, 0.15)]
    assert [f.kind for f in pixel_findings(scan(draw), text_place, 5)] == ["COPIED_PATCH"]
    assert pixel_findings(scan(draw), [], 5) == []     # no word boxes: text not masked
    assert pixel_findings(scan(stamp), [word("(2/5)", 0.5, 0.02)], 5) == []
