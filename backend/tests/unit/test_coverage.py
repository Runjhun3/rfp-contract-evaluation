from app.config import Settings
from app.forensics.coverage import coverage
from app.schemas.records import Page, Word

SETTINGS = Settings(_env_file=None)
TEXT = "Born-digital letter with enough text to be checked by its text layer, page 3."
WORDS = [Word(text="w", x=0, y=0, w=0, h=0)]


def test_the_coverage_line_names_what_could_not_be_checked_and_why():
    pages = {3: Page(pdf_page_no=3, text=TEXT),
             5: Page(pdf_page_no=5, text="", image_dpi=96, ocr_words=WORDS),
             6: Page(pdf_page_no=6, text="", image_dpi=72, ocr_words=WORDS),
             7: Page(pdf_page_no=7, text="", image_dpi=200)}
    line = coverage([3, 5, 6, 7], pages, {5, 6, 7}, SETTINGS)
    assert line.startswith("Checked p.3, 5, 6, 7 (3 scanned, 1 born-digital): identifiers")
    assert "word positions on 2 pages" in line and "pixels on 1 page" in line
    assert "word checks on 1 page (OCR'd before word positions were kept)" in line
    assert "word positions on 1 page (scanned below 90 dpi)" in line
    assert "pixels on 2 pages (scanned below 150 dpi)" in line


def test_no_cited_page_says_nothing_was_checked():
    assert coverage([], {}, set(), SETTINGS).startswith("No document page")
