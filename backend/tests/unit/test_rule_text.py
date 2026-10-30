from decimal import Decimal as D

import pytest

from app import rule_text

GENERAL = [{"text": "Only completed assignments count.", "rfp_page": 21}]
SCORED = {"criterion_id": "a1", "code": "A.1", "parent_code": None, "stage": "TECHNICAL",
          "kind": "PROJECT", "scored_by": "LLM", "max_marks": D(10), "max_items": 5,
          "allowed": "1, 2", "count_bands": [], "rfp_text": "Similar PMU assignments",
          "meaning": "Completed PMU projects for a government client", "considered": True}
SCREENED = {**SCORED, "criterion_id": "e1", "code": "E.1", "stage": "ELIGIBILITY",
            "kind": None, "max_marks": None, "meaning": "Bid security submitted"}
BEFORE = [SCREENED, SCORED]


@pytest.fixture
def general(monkeypatch):
    known = {"general": GENERAL}
    monkeypatch.setattr(rule_text.q_audit, "latest_general", lambda cur, t: known["general"])
    return known


def saved_text():
    return rule_text.draft(BEFORE, GENERAL)


def test_a_scored_edit_updates_untouched_rule_text_with_its_general_conditions(general):
    after = [SCREENED, dict(SCORED, max_marks=D(12))]
    text, notice = rule_text.after_save(None, "t", (BEFORE, after), saved_text(), saved_text())
    assert notice == rule_text.UPDATED and "max 12 marks" in text
    assert "Only completed assignments count." in text


def test_edits_the_rule_text_does_not_show_change_nothing(general):
    after = [dict(SCREENED, meaning="EMD or exemption", considered=False), SCORED]
    assert rule_text.after_save(None, "t", (BEFORE, after), saved_text(), saved_text()) == (
        saved_text(), None)


def test_the_committees_own_rule_text_is_kept(general):
    after = [SCREENED, dict(SCORED, max_marks=D(12))]
    typed = saved_text() + "\nCount joint ventures once."
    # typed in this save
    assert rule_text.after_save(None, "t", (BEFORE, after), saved_text(), typed) == (
        typed, rule_text.KEPT)
    # saved earlier, and sent unchanged now
    assert rule_text.after_save(None, "t", (BEFORE, after), typed, typed) == (
        typed, rule_text.KEPT)


def test_without_a_recorded_extraction_the_general_conditions_are_read_back(general):
    general["general"] = None                          # a project read before migration 016
    after = [SCREENED, dict(SCORED, max_marks=D(12))]
    text, notice = rule_text.after_save(None, "t", (BEFORE, after), saved_text(), saved_text())
    assert notice == rule_text.UPDATED and text == rule_text.draft(after, GENERAL)
    assert rule_text.read_back(saved_text()) == GENERAL
    rebuilt = rule_text.rebuilt(None, "t", after, saved_text())
    assert rebuilt == {"text": text, "recorded": False}


def test_read_back_conditions_are_kept_as_written_and_other_edits_block_the_update(general):
    general["general"] = None
    after = [SCREENED, dict(SCORED, max_marks=D(12))]
    # A general condition reworded by hand is read back as written, so it is kept.
    reworded = saved_text().replace("Only completed", "Only fully completed")
    text, notice = rule_text.after_save(None, "t", (BEFORE, after), reworded, reworded)
    assert notice == rule_text.UPDATED and "Only fully completed" in text
    # Any other hand edit: the committee's text is kept.
    noted = saved_text() + "\nCount joint ventures once."
    assert rule_text.after_save(None, "t", (BEFORE, after), noted, noted) == (
        noted, rule_text.KEPT)
