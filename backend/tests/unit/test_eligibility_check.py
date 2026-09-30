import json
from datetime import date

from app.config import Settings
from app.evaluate.eligibility_check import check_requirement, verify
from app.ingest.extract_criteria import ExtractedCriterion, merge
from app.ingest.label_pages import label_pages
from app.llm.client import LlmClient
from app.schemas.records import Page, Requirement

SETTINGS = Settings(_env_file=None)
AS_OF = date(2026, 5, 7)
REQ = Requirement(criterion_id="e2", code="E.2", title="Turnover",
                  meaning="Average annual turnover of at least 50 crore",
                  rfp_text="Average turnover of the last 3 years at least INR 50 Crore",
                  proof="CA certificate")


def llm_answering(tmp_path, answer: dict, calls: list) -> LlmClient:
    def fake(system, user, images):
        calls.append(user)
        return json.dumps(answer)
    return LlmClient(Settings(_env_file=None, llm_cache_dir=str(tmp_path)), completer=fake)


def pages(**tags) -> dict[int, Page]:
    return {1: Page(pdf_page_no=1, text="Index of documents"),
            41: Page(pdf_page_no=41, text="Average turnover (3 years): Rs. 61.20 crore",
                     eligibility=tags.get("p41", [])),
            44: Page(pdf_page_no=44, text="", ocr_text="Balance sheet FY 2024-25",
                     eligibility=tags.get("p44", []))}


def test_a_requirement_with_no_proof_page_is_unsure_without_an_ai_call(tmp_path):
    calls = []
    result, tagged = check_requirement(REQ, "Firm A", pages(), "system",
                                       llm_answering(tmp_path, {}, calls))
    assert (result.result, tagged, calls) == ("UNSURE", [], [])
    assert "CA certificate" in result.finding


def test_only_the_tagged_pages_are_sent_and_the_answer_is_verified(tmp_path):
    calls = []
    answer = {"code": "X", "result": "met", "finding": "CA certificate shows 61.2 crore.",
              "facts": {"average_turnover_inr": {"value": "612000000", "page": 41,
                                                 "quote": "Average turnover (3 years): Rs. "
                                                          "61.20 crore"},
                        "certified_on": {"value": "2026-04-30", "page": 44,
                                         "quote": "Certified on 30 April 2026"}},
              "conditions": [{"fact": "average_turnover_inr", "test": ">=",
                              "threshold": "500000000", "met": False}]}
    bid = pages(p41=["E.2"], p44=["E.2", "E.9"])
    result, tagged = check_requirement(REQ, "Firm A", bid, "system",
                                       llm_answering(tmp_path, answer, calls))
    assert (result.code, result.result, tagged) == ("E.2", "MET", [41, 44])
    assert "[PDF p. 41]" in calls[0] and "[PDF p. 1]" not in calls[0]
    assert "CA certificate" in calls[0]                       # the proof the RFP asks for
    checks = {c.fact: c for c in verify(result, tagged, bid, SETTINGS, AS_OF)}
    assert checks["average_turnover_inr"].passed()
    assert not checks["certified_on"].quote_found              # not on its page
    test = checks["condition: average_turnover_inr >= 500000000"]
    assert test.value_matches is False                         # the AI said not met


def test_an_unknown_result_is_read_as_unsure(tmp_path):
    answer = {"code": "E.2", "result": "PROBABLY", "finding": "Hard to say."}
    result, _ = check_requirement(REQ, "Firm A", pages(p41=["E.2"]), "system",
                                  llm_answering(tmp_path, answer, []))
    assert result.result == "UNSURE"


def test_labels_keep_only_known_requirement_codes(tmp_path):
    answer = {"pages": [{"pdf_page_no": 41, "page_type": "CA_CERT",
                         "eligibility": ["E.2", "E.99"]}]}
    calls = []
    labelled = label_pages([Page(pdf_page_no=41, text="CA certificate")], [],
                           llm_answering(tmp_path, answer, calls), [REQ])
    assert labelled[0].eligibility == ["E.2"]
    assert "E.2 — Average annual turnover of at least 50 crore — proof: CA certificate" \
        in calls[0]


def test_merging_chunks_keeps_the_proof_whichever_chunk_found_it():
    def row(proof):
        return ExtractedCriterion(code="E.1", stage="ELIGIBILITY", title="Turnover",
                                  rfp_text="t", meaning="m", proof=proof)
    merged = merge([row(None), row("CA certificate as per the format")])
    assert len(merged) == 1 and merged[0].proof == "CA certificate as per the format"


def test_required_documents_are_numbered_apart_from_eligibility_criteria():
    def row(code, stage, title):
        return ExtractedCriterion(code=code, stage=stage, title=title, rfp_text="t",
                                  meaning="m")
    merged = merge([row("E.1", "ELIGIBILITY", "EMD"), row("E.2", "DOCUMENT", "Bid form"),
                    row("E.1", "DOCUMENT", "Power of attorney"),
                    row("A.1", "TECHNICAL", "Projects")])
    assert [(c.code, c.stage) for c in merged] == [
        ("E.1", "ELIGIBILITY"), ("D.1", "DOCUMENT"), ("D.2", "DOCUMENT"), ("A.1", "TECHNICAL")]
