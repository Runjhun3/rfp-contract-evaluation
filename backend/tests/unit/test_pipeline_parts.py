import json

import pytest

from app.config import Settings
from app.ingest.build_items import build_items
from app.llm.client import LlmClient, ReplayMiss
from app.llm.prompts import PromptError, fill, load
from app.schemas.llm import PageLabels
from app.schemas.records import Page


def _page(n, kind=None, code=None, start=False):
    return Page(pdf_page_no=n, text=f"Page {n} Credential header text", page_type=kind,
                criterion_code=code, map_confidence=0.9, item_start=start)


def test_build_items_splits_on_headers_and_sections():
    pages = [_page(1, "CLAIM_SUMMARY", "A.1"), _page(2, "PROJECT_HEADER", "A.1", True),
             _page(3, "WORK_ORDER"), _page(4, "COMPLETION_CERT"),
             _page(5, "PROJECT_HEADER", "A.1", True), _page(6, "CA_CERT"),
             _page(7, "CLAIM_SUMMARY", "A.2"), _page(8, "PROJECT_HEADER", None, True),
             _page(9, "WORK_ORDER"), _page(10, "CV", "B.2", True), _page(11, "CV")]
    items = build_items(pages)
    assert [(i.label, i.kind) for i in items] == [
        ("A.1 p.2-4", "PROJECT"), ("A.1 p.5-6", "PROJECT"), ("B.2 p.10-11", "CV")]


def test_prompt_fill_requires_every_placeholder():
    with pytest.raises(PromptError):
        fill("Hello {{name}} {{other}}", name="x")
    assert "{{" not in fill(load("criterion"), code="A.1", bidder="B", max_items=8,
                            max_marks=16, item_results="[]")


def test_llm_client_retries_bad_json_then_caches(tmp_path):
    answers = iter(["not json", json.dumps({"pages": [{"pdf_page_no": 1, "page_type": "CV"}]})])
    calls = []

    def fake(system, user):
        calls.append(user)
        return next(answers)

    settings = Settings(_env_file=None, llm_cache_dir=str(tmp_path))
    llm = LlmClient(settings, completer=fake)
    assert llm.ask_json("s", "u", PageLabels).pages[0].page_type == "CV"
    assert len(calls) == 2 and "could not be used" in calls[1]
    replay = LlmClient(Settings(_env_file=None, llm_cache_dir=str(tmp_path), llm_mode="replay"))
    with pytest.raises(ReplayMiss):
        replay.complete("s", "never asked")
