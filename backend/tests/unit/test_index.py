import numpy as np

from app.forensics import index
from app.forensics.images import Scan
from app.schemas.records import Page

BOX = {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}
# A made-up bid of 40 scanned pages and one born-digital page.
PAGES = {n: Page(pdf_page_no=n, text="", image_dpi=None if n == 41 else 100)
         for n in range(1, 42)}


def test_only_the_cited_pages_are_analysed_each_once_and_a_job_sees_only_its_own(
        tmp_path, monkeypatch):
    analysed = []

    def scan(pdf, n):
        analysed.append(n)
        return Scan(pixels=np.full((80, 60, 3), 255, np.uint8), box=BOX, jpeg=False, dpi=100)

    monkeypatch.setattr(index, "page_scan", scan)
    monkeypatch.setattr(index, "find_marks", lambda scan, words: [])
    monkeypatch.setattr(index, "own_images", lambda pdf: [])
    first = index.bid_index(None, PAGES, tmp_path, [3, 7, 41, 99])
    assert analysed == [3, 7] and set(first.boxes) == {3, 7}         # 41 has no scan
    second = index.bid_index(None, PAGES, tmp_path, [7, 12])          # a later job
    assert analysed == [3, 7, 12]                                     # 7 was kept
    assert set(second.boxes) == {7, 12} and set(second.thumbs) == {7, 12}
    assert (tmp_path / index.NAME).exists() and not (tmp_path / "index-v2.part").exists()
