import json

import pytest

from app.config import Settings
from app.ingest.build_items import build_items
from app.llm.client import LlmClient, ReplayMiss
from app.llm.prompts import PromptError, fill, load
from app.schemas.llm import PageLabels
from app.schemas.records import Page


KINDS = {"A.1": "PROJECT", "A.2": "PROJECT", "A.3": "PROJECT", "B.1": "CV", "B.2": "CV"}


def _page(n, kind=None, code=None, start=False, title=None):
    return Page(pdf_page_no=n, text=f"Page {n} Credential header text", page_type=kind,
                criterion_code=code, map_confidence=0.9, item_start=start, title=title)


def test_build_items_splits_on_headers_and_sections():
    pages = [_page(1, "CLAIM_SUMMARY", "A.1"), _page(2, "PROJECT_HEADER", "A.1", True),
             _page(3, "WORK_ORDER"), _page(4, "COMPLETION_CERT"),
             _page(5, "PROJECT_HEADER", "A.1", True), _page(6, "CA_CERT"),
             _page(7, "CLAIM_SUMMARY", "A.2"), _page(8, "PROJECT_HEADER", None, True),
             _page(9, "WORK_ORDER"), _page(10, "CV", "B.2", True), _page(11, "CV")]
    items = build_items(pages, KINDS)
    assert [(i.label, i.kind) for i in items] == [
        ("A.1 p.2-4", "PROJECT"), ("A.1 p.5-6", "PROJECT"), ("A.2 p.8-9", "PROJECT"),
        ("B.2 p.10-11", "CV")]


def test_the_bidders_section_decides_the_criterion_not_the_page_content():
    # p.3 reads like A.3 by content, but the bidder claims it in its A.1 section.
    pages = [_page(1, "CLAIM_SUMMARY", "A.1"), _page(2, "PROJECT_HEADER", "A.1", True),
             _page(3, "PROJECT_HEADER", "A.3", True, title="Games planning"),
             _page(4, "WORK_ORDER"), _page(5, "MARKETING"),
             _page(6, "PROJECT_HEADER", "A.3", True)]
    items = build_items(pages, KINDS)
    assert [i.label for i in items] == ["A.1 p.2-2", "A.1 p.3-4", "A.3 p.6-6"]
    assert items[1].title == "Games planning"


def test_a_summary_for_several_criteria_leaves_each_cv_its_own_label():
    # One team table covering two positions (criterion_code null) opens no section,
    # and a project section never swallows CVs.
    pages = [_page(1, "CLAIM_SUMMARY", "A.1"), _page(2, "PROJECT_HEADER", "A.1", True),
             _page(3, "CV", "B.1", True), _page(4, "CLAIM_SUMMARY", None),
             _page(5, "CV", "B.1", True), _page(6, "CV", "B.2", True)]
    assert [i.label for i in build_items(pages, KINDS)] == [
        "A.1 p.2-2", "B.1 p.3-3", "B.1 p.5-5", "B.2 p.6-6"]


def test_prompt_fill_requires_every_placeholder():
    with pytest.raises(PromptError):
        fill("Hello {{name}} {{other}}", name="x")
    assert "{{" not in fill(load("criterion"), code="A.1", bidder="B", max_items=8,
                            max_marks=16, item_results="[]")


def test_llm_client_retries_bad_json_then_caches(tmp_path):
    answers = iter(["not json", json.dumps({"pages": [{"pdf_page_no": 1, "page_type": "CV"}]})])
    calls = []

    def fake(system, user, images):
        calls.append(user)
        return next(answers)

    settings = Settings(_env_file=None, llm_cache_dir=str(tmp_path))
    llm = LlmClient(settings, completer=fake)
    assert llm.ask_json("s", "u", PageLabels).pages[0].page_type == "CV"
    assert len(calls) == 2 and "could not be used" in calls[1]
    replay = LlmClient(Settings(_env_file=None, llm_cache_dir=str(tmp_path), llm_mode="replay"))
    with pytest.raises(ReplayMiss):
        replay.complete("s", "never asked")


def test_the_same_persons_cv_twice_under_one_criterion_is_scored_once():
    pages = [_page(1, "CV", "B.2", True, title="Parul Saini, Senior Consultant"),
             _page(2, "CV"), _page(3, "CV"),
             _page(4, "CV", "B.2", True, title="Anand Gupta, Senior Consultant"),
             _page(5, "CV", "B.2", True, title="PARUL  SAINI, Sr. Consultant"),   # 1-page profile
             _page(6, "CV", "B.1", True, title="Parul Saini, Project Manager"),   # other criterion
             _page(7, "CV", "B.2", True), _page(8, "CV", "B.2", True)]           # no names
    items = {i.label: i for i in build_items(pages, KINDS)}
    assert items["B.2 p.5-5"].duplicate_of == "B.2 p.1-3"
    assert [label for label, i in items.items() if i.duplicate_of] == ["B.2 p.5-5"]


def test_a_cv_keeps_the_position_it_names_after_a_mixed_team_summary():
    # A team summary over four pages: a cover and a Project Manager page (no single
    # criterion), then two Senior Consultant pages. The Project Manager's CV must stay
    # under its own position, not the last summary page's.
    pages = [_page(1, "CLAIM_SUMMARY", None), _page(2, "CLAIM_SUMMARY", None),
             _page(3, "CLAIM_SUMMARY", "B.2"), _page(4, "CLAIM_SUMMARY", "B.2"),
             _page(5, "CV", "B.1", True, title="Asha Rao, Project Manager"), _page(6, "CV"),
             _page(7, "CV", "B.2", True, title="Ravi Jain, Senior Consultant")]
    assert [i.label for i in build_items(pages, KINDS)] == ["B.1 p.5-6", "B.2 p.7-7"]


def test_a_multi_page_summary_for_one_criterion_still_opens_a_section():
    pages = [_page(1, "CLAIM_SUMMARY", "A.1"), _page(2, "CLAIM_SUMMARY", "A.1"),
             _page(3, "PROJECT_HEADER", "A.3", True)]
    assert [i.label for i in build_items(pages, KINDS)] == ["A.1 p.3-3"]


def test_a_criterion_with_nothing_found_says_where_its_kind_went():
    from app.pipeline import nothing_found
    from app.schemas.records import Criterion, Item
    crit = Criterion(code="B.1", title="t", meaning="m", kind="CV", max_marks=8,
                     allowed_item_marks=[])
    items = [Item(label="B.2 p.5-6", title="Asha Rao, Project Manager", kind="CV",
                  criterion_code="B.2", map_confidence=0.9, from_page=5, to_page=6)]
    assert nothing_found(crit, items) == (
        "No CV was assigned to B.1, so it scores 0. CVs found in the bid: "
        "p.5-6 Asha Rao, Project Manager (assigned to B.2).")
    assert nothing_found(crit, []).endswith("No CV pages were found in the bid.")


def test_a_whole_bid_criterion_gets_one_item_of_all_its_evidence_pages():
    kinds = {**KINDS, "F.1": "BID", "F.2": "BID"}
    pages = [_page(1, "CLAIM_SUMMARY", "A.1"), _page(2, "PROJECT_HEADER", "A.1", True),
             _page(3, "CA_CERT", "F.1"), _page(4, "WORK_ORDER"), _page(9, "OTHER", "F.1")]
    bid = [i for i in build_items(pages, kinds) if i.kind == "BID"]
    assert [(i.label, i.pages, i.page_list()) for i in bid] == [
        ("F.1 p.3-9", [3, 9], [3, 9])]                     # F.2 has no evidence: no item
