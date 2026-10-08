from datetime import date

from app.config import Settings
from app.evaluate.document_checks import CLAIM, REFERENCE, RESOLUTION, document_checks
from app.evaluate.date_order import DATE_ORDER
from app.evaluate.stated_sums import STATED_SUM
from app.schemas.documents import Discrepancy, Reference, StatedSum
from app.schemas.llm import Fact, ItemResult
from app.schemas.records import Item, Page

SETTINGS = Settings(_env_file=None)
DUE = date(2026, 3, 31)
ITEM = Item(label="A.1 p.10-12", title="Stadium PMU", kind="PROJECT", criterion_code="A.1",
            map_confidence=0.9, from_page=10, to_page=12)
PAGES = {2: Page(pdf_page_no=2, text="Claim table: Stadium PMU value INR 5.20 Cr"),
         10: Page(pdf_page_no=10, text="Work order dated 01.04.2021 for Stadium PMU"),
         11: Page(pdf_page_no=11, text="Contract value Rs. 2,50,00,000 till 31.03.2023"),
         12: Page(pdf_page_no=12, text="Completion certificate issued on 15.05.2023 as per "
                                       "the amendment dated 10.10.2022", image_dpi=80)}


def fact(value, page, quote):
    return Fact(value=value, page=page, quote=quote)


def result(**extra):
    facts = {"awarded_on": fact("2021-04-01", 10, "Work order dated 01.04.2021"),
             "start_on": fact("2021-04-01", 10, "Work order dated 01.04.2021"),
             "end_on": fact("2023-03-31", 11, "till 31.03.2023"),
             "is_completed": fact("true", 12, "Completion certificate"),
             "certificate_on": fact("2023-05-15", 12, "issued on 15.05.2023")}
    facts.update(extra.pop("facts", {}))
    return ItemResult(label=ITEM.label, code="A.1", facts=facts, eligible=True, marks=1,
                      reason="ok", confidence=0.9, **extra)


def checks(r):
    return {c.fact: c for c in document_checks(r, ITEM, PAGES, SETTINGS, DUE)}


def test_dates_in_order_pass_and_each_problem_is_named():
    assert checks(result())[DATE_ORDER].value_matches is True
    early = checks(result(facts={"certificate_on": fact("2023-02-01", 12, "issued on 15.05.2023")}))
    assert early[DATE_ORDER].value_matches is True       # its quote does not state that date
    pages = {**PAGES, 12: Page(pdf_page_no=12, text="issued on 01.05.2026")}
    late = result(facts={"certificate_on": fact("2026-05-01", 12, "issued on 01.05.2026")})
    found = {c.fact: c for c in document_checks(late, ITEM, pages, SETTINGS, DUE)}
    assert found[DATE_ORDER].value_matches is False
    assert "after the bid due date" in found[DATE_ORDER].note
    swapped = checks(result(facts={"start_on": fact("2023-06-01", 10, "dated 01.04.2021")}))
    assert "starts (1 Jun 2023) after it ends (31 Mar 2023)" in swapped[DATE_ORDER].note


def test_a_stated_average_is_recomputed():
    figures = {"y1_inr": fact("100", 11, "x"), "y2_inr": fact("200", 11, "x"),
               "avg_inr": fact("150", 11, "x"), "bad_inr": fact("170", 11, "x")}
    good = StatedSum(result="avg_inr", op="average", parts=["y1_inr", "y2_inr"])
    bad = StatedSum(result="bad_inr", op="average", parts=["y1_inr", "y2_inr"])
    assert checks(result(facts=figures, sums=[good]))[STATED_SUM].value_matches is True
    wrong = checks(result(facts=figures, sums=[bad]))[STATED_SUM]
    assert wrong.value_matches is False and "the figures give 150" in wrong.note


def test_a_claim_differing_from_its_document_needs_both_quotes_on_their_pages():
    real = Discrepancy(about="contract value", claim=fact("5.20 Cr", 2, "value INR 5.20 Cr"),
                       document=fact("2.50 Cr", 11, "Contract value Rs. 2,50,00,000"))
    found = checks(result(discrepancies=[real]))[CLAIM]
    assert found.value_matches is False and "the firm's page says \"5.20 Cr\" (p.2)" in found.note
    made_up = real.model_copy(update={"claim": fact("9 Cr", 2, "value INR 9 Cr")})
    assert checks(result(discrepancies=[made_up]))[CLAIM].value_matches is None


def test_a_document_referred_to_but_not_in_the_item_is_flagged():
    missing = Reference(document="the amendment dated 10.10.2022", page=12,
                        quote="as per the amendment dated 10.10.2022")
    assert checks(result(references=[missing]))[REFERENCE].value_matches is False
    present = missing.model_copy(update={"found_on_page": 11})
    assert REFERENCE not in checks(result(references=[present]))


def test_evidence_from_a_low_resolution_scan_is_flagged():
    low = checks(result())[RESOLUTION]
    assert low.value_matches is False and "p.12 (about 80 dpi)" in low.note


class FakeChecker:
    """Stands in for forensics.checker.DocumentChecker."""

    def __init__(self):
        from app.evaluate.identifiers import Found
        from app.forensics.finding import Finding
        self.ids = [Found(kind="GSTIN", value="X1", pages=[11], ok=False, note="Bad digit."),
                    Found(kind="CIN", value="U1", pages=[11], ok=True, note="Valid."),
                    Found(kind="BANK_GUARANTEE", value="B1", pages=[12], ok=None,
                          note="Only the bank can confirm it.")]
        self.box = {"x": 0.5, "y": 0.4, "w": 0.1, "h": 0.02}
        self.found = [Finding(kind="GEOMETRY", page=12, region=self.box, score=2,
                              note="Off line.")]

    def identifiers(self, pages):
        return self.ids

    def forensic(self, pages):
        return self.found

    def coverage(self, pages):
        return f"Checked {len(pages)} pages."


def test_every_document_check_is_shown_but_only_problems_change_the_verdict():
    from app.evaluate.document_checks import COVERAGE, FORENSIC, IDENTIFIER, cited_pages
    from app.evaluate.document_flags import document_flags
    checker = FakeChecker()
    rows = document_flags("A.1", [11, 12], checker, SETTINGS)
    assert [(c.fact, c.value_matches) for c in rows] == [
        (IDENTIFIER, False), (IDENTIFIER, True), (IDENTIFIER, None), (FORENSIC, None),
        (COVERAGE, True)]
    assert rows[0].note == "GSTIN X1: Bad digit. Confirm with the GST portal " \
                           "(services.gst.gov.in)."
    look = rows[3]                         # uncalibrated: a note, with its box on the page
    assert look.region == checker.box and look.note.startswith("On p.12, Off line. A note")
    counted = document_flags("A.1", [11, 12], checker,
                             Settings(_env_file=None, forensic_flags=True))[3]
    assert (counted.value_matches, counted.note) == (False, "On p.12, Off line.")
    assert document_flags("A.1", [], checker, SETTINGS)[-1].value_matches is None
    r = result(discrepancies=[])
    assert cited_pages(r, ITEM) == [10, 10, 11, 12, 12]      # the documents the facts cite


def test_an_eligibility_checks_documents_are_the_pages_its_facts_are_quoted_from():
    from app.evaluate import eligibility_check
    from app.schemas.llm import EligibilityResult
    answer = EligibilityResult(code="E.5", result="MET", finding="ok",
                               facts={"value_inr": fact("5", 40, "x"),
                                      "end_on": fact("2023-03-31", 42, "x"),
                                      "outside": fact("1", 99, "x"), "missing": None})
    # Tagged 30-60 (a whole project section); only the two quoted pages are checked.
    assert eligibility_check.cited_pages(answer, list(range(30, 61))) == [40, 42]
