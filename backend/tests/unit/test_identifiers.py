from app.evaluate.identifiers import find_identifiers, gstin_check_digit
from app.schemas.records import Page

# Made-up identifiers only: a GSTIN built with its own check digit, and its corruption.
BODY = "29ABCDE1234F1Z"
GSTIN = BODY + gstin_check_digit(BODY)
WRONG = BODY + ("A" if GSTIN[-1] != "A" else "B")


def found(*texts):
    pages = [Page(pdf_page_no=n, text=t) for n, t in enumerate(texts, start=1)]
    return {(f.kind, f.value): f for f in find_identifiers(pages)}


def test_a_gstin_is_checked_by_its_check_digit_and_listed_once_with_its_pages():
    got = found(f"GSTIN: {GSTIN}", f"Registered GSTIN {GSTIN}", f"GST {WRONG}")
    assert got[("GSTIN", GSTIN)].ok is True and got[("GSTIN", GSTIN)].pages == [1, 2]
    assert got[("GSTIN", WRONG)].ok is False


def test_a_udin_must_carry_the_membership_number_and_year_printed_on_its_page():
    page = ("Chartered Accountants. Partner M. No. 123456 UDIN: 26123456ABCDEF1234 "
            "Date: 02 April 2026")
    assert found(page)[("UDIN", "26123456ABCDEF1234")].ok is True
    other = found(page.replace("M. No. 123456", "M. No. 654321"))
    assert other[("UDIN", "26123456ABCDEF1234")].ok is False
    assert "membership number 123456 is not the M. No." in \
        other[("UDIN", "26123456ABCDEF1234")].note


def test_a_ca_certificate_without_a_udin_is_listed_with_its_pages():
    page = "For Example & Co, Chartered Accountants, Membership No. 123456"
    got = found(page, "Annual turnover statement", page)
    assert got[("MISSING_UDIN", "")].pages == [1, 3] and got[("MISSING_UDIN", "")].ok is False


def test_a_persons_pan_is_never_listed_an_organisations_is():
    got = found("Company PAN: ABCCD1234E", "Partner's PAN: ABCPD1234E")
    assert ("PAN", "ABCCD1234E") in got and ("PAN", "ABCPD1234E") not in got


def test_registrations_and_bank_guarantees_are_listed():
    got = found("CIN U74999DL2010PTC123456", "LLPIN: AAA-1234", "BG No. 0123BG000456")
    assert got[("CIN", "U74999DL2010PTC123456")].ok is True
    assert ("LLPIN", "AAA-1234") in got and ("BANK_GUARANTEE", "0123BG000456") in got
    assert got[("BANK_GUARANTEE", "0123BG000456")].ok is None     # only the bank can say
