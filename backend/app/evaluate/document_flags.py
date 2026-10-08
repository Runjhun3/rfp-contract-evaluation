"""The document checks of a criterion check's evidence pages (D-059, D-062, D-063): only
the pages its verdict rests on, as rows of the check's own verification, so they are
shown and decided with it. Every row is shown:
  - each identifier: valid (passed), a problem (the check is for the committee), or one
    only its issuer can confirm (a note); each says where to confirm it;
  - each forensic finding, with its box on the page: a note to look at, which does not
    change the verdict until the checks are calibrated (FORENSIC_FLAGS), then a problem;
  - what was checked and what could not be (coverage.py), so nothing found is never
    mistaken for never checked.
"""
from app.config import Settings
from app.evaluate.document_checks import COVERAGE, FORENSIC, IDENTIFIER
from app.schemas.records import EvidenceCheck

# Where the committee can confirm each identifier; the app itself never looks anything up.
CONFIRM_AT = {"UDIN": "ICAI's UDIN portal (udin.icai.org)",
              "MISSING_UDIN": "the CA (ask for the UDIN; udin.icai.org confirms it)",
              "GSTIN": "the GST portal (services.gst.gov.in)",
              "CIN": "the MCA portal (mca.gov.in)", "LLPIN": "the MCA portal (mca.gov.in)",
              "PAN": "the Income Tax portal (incometax.gov.in)",
              "BANK_GUARANTEE": "the issuing bank's branch"}
TO_LOOK = " A note to look at: it does not change the result."


def document_flags(label: str, page_nos: list[int], checker,
                   settings: Settings) -> list[EvidenceCheck]:
    """checker: the bid file's DocumentChecker."""
    checks = [_identifier(label, f) for f in checker.identifiers(page_nos)]
    counted = settings.forensic_flags
    checks += [EvidenceCheck(label=label, fact=FORENSIC, quote_found=True,
                             value_matches=False if counted else None, pdf_page_no=f.page,
                             region=f.region, note=f"On p.{f.page}, {f.note.rstrip('.')}."
                             + ("" if counted else TO_LOOK))
               for f in checker.forensic(page_nos)]
    return checks + [EvidenceCheck(label=label, fact=COVERAGE, quote_found=True,
                                   value_matches=True if page_nos else None,
                                   pdf_page_no=min(page_nos) if page_nos else None,
                                   note=checker.coverage(page_nos))]


def _identifier(label: str, found) -> EvidenceCheck:
    """found: an identifiers.Found; ok True valid, False a problem, None issuer only."""
    note = f"{found.kind} {found.value}: {found.note}".replace(" :", ":")
    if found.kind in CONFIRM_AT:
        note += f" Confirm with {CONFIRM_AT[found.kind]}."
    return EvidenceCheck(label=label, fact=IDENTIFIER, quote_found=True,
                         value_matches=found.ok, pdf_page_no=found.pages[0], note=note)
