"""The identifiers in one bid that the committee can confirm with their issuer, found
in each page's text (text layer and OCR), with the checks that need no issuer:
  - UDIN (a CA's certificate number): its embedded membership number and year must
    match the "M. No." and a date on the same page; a CA certificate without a UDIN
    is listed too,
  - GSTIN: format and check digit, so a mistyped or invented number shows,
  - CIN and LLPIN (company and LLP registrations): format,
  - PAN of an organisation (a person's PAN is personal data and is never listed),
  - bank guarantee numbers: listed for the bank to confirm.
A failed check may be an OCR misreading: the committee confirms with the issuer.
"""
import re
from datetime import date

from pydantic import BaseModel

from app.evaluate.parse_date import parse_dates
from app.schemas.records import Page

_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b")
_CIN = re.compile(r"\b[LU]\d{5}[A-Z]{2}(\d{4})[A-Z]{3}\d{6}\b")
_UDIN = re.compile(r"UDIN\W{0,3}([0-9]{8}[A-Z0-9]{10})\b")
_LLPIN = re.compile(r"LLPIN\W{0,3}([A-Z]{3}-?\d{4})\b")
_PAN = re.compile(r"\bPAN(?:\s*NO\.?)?\W{0,3}([A-Z]{3}([A-Z])[A-Z]\d{4}[A-Z])\b")
_BG = re.compile(r"(?:\bB\.?\s?G\.?|BANK\s+GUARANTEE)\s*(?:NO|NUMBER)\.?\W{0,3}"
                 r"([A-Z0-9][A-Z0-9/-]{5,})")
_MEMBER = re.compile(r"(?:M\.?\s*NO\.?|MEMBERSHIP\s*(?:NO\.?|NUMBER))\W{0,3}(\d{5,6})\b")
_CA_PAGE = re.compile(r"CHARTERED\s+ACCOUNTANT", re.I)
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ORG_PAN = set("ABCFGHJLT")      # the 4th letter of a PAN: P is a person, never listed


class Found(BaseModel):
    kind: str                     # UDIN, MISSING_UDIN, GSTIN, CIN, LLPIN, PAN, BANK_GUARANTEE
    value: str = ""
    pages: list[int]
    ok: bool | None = None        # None: nothing to check without the issuer
    note: str = ""


def find_identifiers(pages: list[Page]) -> list[Found]:
    """Every identifier in the bid, once per value, with the pages it is on (CA
    certificates without a UDIN as one finding listing their pages)."""
    found: dict[tuple[str, str], Found] = {}
    for page in pages:
        for f in _on_page(page):
            key = (f.kind, f.value)
            if key in found:
                found[key].pages.append(page.pdf_page_no)
            else:
                found[key] = f
    return list(found.values())


def _on_page(page: Page) -> list[Found]:
    text, n = page.full_text().upper(), page.pdf_page_no
    out = [_udin(m[1], text, n) for m in _UDIN.finditer(text)]
    if not out and _CA_PAGE.search(text) and _MEMBER.search(text):
        out.append(Found(kind="MISSING_UDIN", pages=[n], ok=False,
                         note="A CA's certificate with no UDIN on the page."))
    out += [_gstin(m[0], n) for m in _GSTIN.finditer(text)]
    out += [_cin(m[0], int(m[1]), n) for m in _CIN.finditer(text)]
    out += [Found(kind="LLPIN", value=m[1], pages=[n], ok=True) for m in _LLPIN.finditer(text)]
    out += [Found(kind="PAN", value=m[1], pages=[n], ok=True) for m in _PAN.finditer(text)
            if m[2] in _ORG_PAN]
    out += [Found(kind="BANK_GUARANTEE", value=m[1], pages=[n]) for m in _BG.finditer(text)]
    return out


def _udin(udin: str, text: str, page: int) -> Found:
    problems = []
    members = {m[1].zfill(6) for m in _MEMBER.finditer(text)}
    if members and udin[2:8] not in members:
        problems.append(f"its membership number {udin[2:8]} is not the M. No. on the page "
                        f"({', '.join(sorted(members))})")
    years = {d.year for d in parse_dates(text)[0]}
    if years and 2000 + int(udin[:2]) not in years:
        problems.append(f"its year 20{udin[:2]} is not the year of any date on the page")
    note = "Matches the M. No. and date on the page." if not problems else \
        "UDIN " + "; ".join(problems) + "."
    return Found(kind="UDIN", value=udin, pages=[page], ok=not problems, note=note)


def gstin_check_digit(first14: str) -> str:
    """The GSTIN check character of its first 14 characters (mod 36)."""
    total = 0
    for i, ch in enumerate(first14):
        product = _CHARS.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return _CHARS[(36 - total % 36) % 36]


def _gstin(gstin: str, page: int) -> Found:
    ok = gstin_check_digit(gstin[:14]) == gstin[14] and 1 <= int(gstin[:2]) <= 99
    note = "Format and check digit are valid." if ok else \
        "The check digit does not match: mistyped, misread by OCR, or not a real GSTIN."
    return Found(kind="GSTIN", value=gstin, pages=[page], ok=ok, note=note)


def _cin(cin: str, year: int, page: int) -> Found:
    ok = 1850 <= year <= date.today().year
    note = "Format is valid." if ok else f"Its year of registration ({year}) is not possible."
    return Found(kind="CIN", value=cin, pages=[page], ok=ok, note=note)
