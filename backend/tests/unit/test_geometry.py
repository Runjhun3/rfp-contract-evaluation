from app.forensics.finding import is_figure
from app.forensics.geometry import check_words
from app.forensics.lines import group_lines
from app.schemas.records import Word


def line(y=0.5, h=0.012, texts=("Completed", "on", "12.05.2023", "for", "Client", "Ltd"),
         font="Georgia", size=11.0, shift=None):
    """One typed line of made-up words, 0.08 apart; shift: {index: (dy, dh, font, size)}."""
    words = []
    for i, text in enumerate(texts):
        dy, dh, f, s = (shift or {}).get(i, (0, 0, font, size))
        words.append(Word(text=text, x=0.1 + 0.12 * i, y=y + dy, w=0.1, h=h + dh,
                          font=f, size=s))
    return words


def notes(words, digital=True):
    return [f.note for f in check_words(words, 1, digital)]


def test_a_figure_sitting_like_its_line_is_not_flagged():
    assert notes(line()) == []


def test_a_figure_off_its_baseline_or_taller_than_its_line_is_flagged():
    off = notes(line(shift={2: (0.006, 0, "Georgia", 11.0)}))
    assert "sits off the line's baseline" in off[0]
    assert "height differs" in notes(line(shift={2: (-0.008, 0.008, "Georgia", 11.0)}))[0]


def test_on_a_text_layer_another_font_or_a_slightly_different_size_is_flagged():
    other = notes(line(shift={2: (0, 0, "Arial", 11.0)}))
    assert "its font (Arial) is not used elsewhere on its line" in other[0]
    assert "its size (12.2)" in notes(line(shift={2: (0, 0, "Georgia", 12.2)}))[0]
    # A subset prefix or a weight is the same typeface.
    assert notes(line(shift={2: (0, 0, "ABCDEF+Georgia-Bold", 11.0)})) == []


def test_a_designed_callout_and_a_scan_without_fonts_are_not_judged_by_font():
    callout = line(shift={2: (0, 0, "Arial", 24.0)})
    assert notes(callout) == []                       # far larger: design, not an edit
    assert notes(line(shift={2: (0, 0, "Arial", 11.0)}), digital=False) == []


def test_page_numbers_contents_leaders_and_page_margins_are_left_out():
    assert not is_figure(Word(text="77", x=0, y=0, w=0, h=0))
    assert not is_figure(Word(text="....12", x=0, y=0, w=0, h=0))
    assert is_figure(Word(text="2023", x=0, y=0, w=0, h=0))
    assert is_figure(Word(text="Rs.2,50,000", x=0, y=0, w=0, h=0))
    footer = line(y=0.97, shift={2: (0.005, 0, "Georgia", 11.0)})
    assert notes(footer) == []


def test_a_table_cell_centred_lower_than_its_neighbours_is_measured_apart():
    row = line(texts=("Value", "Of", "The", "Works"))
    cell = line(y=0.508, texts=("INR", "2,95,000", "till", "2023"))   # centred lower
    for w in cell:
        w.x += 0.5                                                    # its own column
    assert notes(row + cell, digital=False) == []
    pasted = cell[1].model_copy(update={"x": 0.58})                   # right after the text
    assert "sits off the line's baseline" in notes(row + [pasted], digital=False)[0]


def test_handwriting_and_words_ocr_is_unsure_of_are_left_out():
    scan = line(shift={2: (0.008, 0, None, None)}, font=None, size=None)
    assert notes(scan, digital=False) != []
    scan[2].handwritten = True
    assert notes(scan, digital=False) == []
    scan[2].handwritten, scan[2].conf = None, 0.3
    assert notes(scan, digital=False) == []


def test_on_a_slanted_scan_a_figure_is_measured_against_its_lines_slant():
    texts = ("Paid", "On", "The", "Work", "Order", "Of", "Date", "12.05.2023")
    slanted = line(texts=texts, font=None, size=None)
    for i, w in enumerate(slanted):
        w.y -= 0.001 * i                       # each word a little higher, figure included
    assert notes(slanted, digital=False) == []
    slanted[-1].y += 0.008                     # the figure alone dropped below the slant
    assert "sits off the line's baseline" in notes(slanted, digital=False)[0]


def test_a_scan_tolerates_more_wobble_than_a_text_layer():
    wobble = line(shift={2: (0.005, 0, "Georgia", 11.0)})     # 0.42 of a word height
    assert notes(wobble) != [] and notes(wobble, digital=False) == []


def test_words_group_into_lines_left_to_right():
    words = list(reversed(line(y=0.3) + line(y=0.5)))
    lines = group_lines(words)
    assert [len(l) for l in lines] == [6, 6]
    assert [w.text for w in lines[0]][:2] == ["Completed", "on"]
