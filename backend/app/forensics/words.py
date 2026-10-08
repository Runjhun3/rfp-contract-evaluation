"""The words of a page's text layer with their boxes, font and size (pdfium), the
born-digital counterpart of OCR words: a figure typed over or pasted into a digital
document often has a different font or size from the text around it."""
import ctypes
from collections import Counter
from statistics import median, pstdev

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from app.schemas.records import Word


def text_layer_words(pdf: pdfium.PdfDocument, page_no: int) -> list[Word]:
    page = pdf[page_no - 1]
    width, height = page.get_size()
    textpage = page.get_textpage()
    words, chars = [], []
    for i in range(textpage.count_chars()):
        ch = chr(pdfium_c.FPDFText_GetUnicode(textpage.raw, i) or 32)
        if ch.isspace():
            words += _word(chars, width, height)
            chars = []
            continue
        chars.append((ch, textpage.get_charbox(i), _font(textpage, i),
                      pdfium_c.FPDFText_GetFontSize(textpage.raw, i)))
    return words + _word(chars, width, height)


def _word(chars: list[tuple], width: float, height: float) -> list[Word]:
    if not chars:
        return []
    left = min(c[1][0] for c in chars)
    bottom = min(c[1][1] for c in chars)
    right = max(c[1][2] for c in chars)
    top = max(c[1][3] for c in chars)
    font = Counter(c[2] for c in chars).most_common(1)[0][0]
    size = round(sum(c[3] for c in chars) / len(chars), 2)
    return [Word(text="".join(c[0] for c in chars), x=left / width, y=1 - top / height,
                 w=(right - left) / width, h=(top - bottom) / height, font=font, size=size,
                 spacing=_spacing([c[1] for c in chars]))]


def _spacing(boxes: list[tuple]) -> float | None:
    """How uneven the gaps between a word's letters are, in letter widths (0: even);
    None for a word too short to say."""
    if len(boxes) < 4:
        return None
    gaps = [b[0] - a[2] for a, b in zip(boxes, boxes[1:])]
    letter = median(b[2] - b[0] for b in boxes) or 1.0
    return round(pstdev(gaps) / letter, 3)


def _font(textpage: pdfium.PdfTextPage, index: int) -> str:
    buffer = ctypes.create_string_buffer(128)
    flags = ctypes.c_int()
    size = pdfium_c.FPDFText_GetFontInfo(textpage.raw, index, buffer, 128, ctypes.byref(flags))
    return buffer.value.decode("utf-8", "replace") if size else ""
