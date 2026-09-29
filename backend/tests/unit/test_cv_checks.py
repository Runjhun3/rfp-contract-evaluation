from datetime import date
from decimal import Decimal

from app.config import Settings
from app.evaluate.arithmetic_check import check_criterion
from app.evaluate.cv_check import experience_check, total_months
from app.evaluate.evidence_check import check_item
from app.llm.client import LlmClient
from app.schemas.llm import CriterionItem, CriterionResult, CvFacts, ItemResult, Job, SubScore
from app.schemas.records import Criterion, Item, Page

AS_OF = date(2026, 5, 7)
SETTINGS = Settings(_env_file=None)
CV_ITEM = Item(label="B.1 p.5-6", title="t", kind="CV", criterion_code="B.1",
               map_confidence=0.9, from_page=5, to_page=6)
B1 = Criterion(code="B.1", title="t", meaning="m", kind="CV", max_marks=Decimal(8), max_items=1,
               allowed_item_marks=[Decimal(0), Decimal(4), Decimal(8)])


def job(start, end, quote="row", page=5):
    return Job(organisation="Org", role="Manager", start=start, end=end, page=page, quote=quote)


def cv_result(jobs, used="10", scores=("4", "4"), marks="8"):
    cv = CvFacts(employment=jobs, experience_years=Decimal(used) if used else None,
                 sub_scores=[SubScore(name=f"part {n}", marks=Decimal(m))
                             for n, m in enumerate(scores)])
    return ItemResult(label="B.1 p.5-6", code="B.1", cv=cv, eligible=True,
                      marks=Decimal(marks), reason="r", confidence=0.9)


def test_rows_count_both_end_months_with_overlaps_once_and_present_as_bid_date():
    jobs = [job("2012-03", "2013-05"), job("01/2021", "11/2022"),
            job("2022-01", "2022-06"),            # inside the job above: adds nothing
            job("2025-01", "present")]
    assert total_months(jobs, AS_OF) == (15 + 23 + 17, 0)


def test_unreadable_rows_are_counted_not_guessed():
    assert total_months([job("2019", "2020-01"), job("2020-01", "2021-01")], AS_OF) == (13, 1)


def test_back_to_back_jobs_lose_no_month():
    jobs = [job("2017-06", "2018-12"), job("2020-12", "2023-11"), job("2023-12", "2026-05")]
    assert total_months(jobs, AS_OF) == (19 + 36 + 30, 0)      # 85 months: over 7 years


def test_years_that_disagree_with_the_rows_fail_the_check():
    jobs = [job("2012-01", "2022-06")]                     # 10.5 years
    assert experience_check(cv_result(jobs, used="10"), CV_ITEM, AS_OF).passed()
    bad = experience_check(cv_result(jobs, used="5"), CV_ITEM, AS_OF)
    assert not bad.passed() and bad.parsed_value == "10.5" and "used 5" in bad.note


def test_each_employment_row_quote_is_checked_on_its_page():
    pages = {5: Page(pdf_page_no=5, text="1 Lava Intl. Limited Manager 04/2016 02/2018"),
             6: Page(pdf_page_no=6, text="")}
    jobs = [job("2016-04", "2018-02", quote="Lava Intl. Limited Manager 04/2016 02/2018"),
            job("2018-02", "2020-03", quote="Paytm Manager 02/2018 03/2020")]
    result = cv_result(jobs, used="4")
    result.relies_on = ["employment", "experience_years"]   # checked by rows + total, not quotes
    checks = {c.fact: c for c in check_item(result, CV_ITEM, pages, SETTINGS, AS_OF)}
    assert set(checks) == {"employment_row_1", "employment_row_2", "experience_years",
                           "reason and proof"}
    assert checks["employment_row_1"].passed() and not checks["employment_row_2"].passed()
    assert checks["experience_years"].passed()


def test_cv_marks_must_equal_the_sum_of_its_sub_scores():
    good, bad = cv_result([], scores=("4", "4"), marks="8"), cv_result([], scores=("0", "4"))
    row = CriterionItem(label="B.1 p.5-6", order=1, eligible=True, counted=True,
                        marks=Decimal(8), reason="r")
    result = CriterionResult(code="B.1", items=[row], counted_items=1, marks=Decimal(8),
                             summary="s")
    assert check_criterion(B1, result, {"B.1 p.5-6": good}).ok
    issues = check_criterion(B1, result, {"B.1 p.5-6": bad}).issues
    assert issues == ["B.1 p.5-6: sub-criteria add up to 4, item said 8"]


def test_page_images_are_sent_and_are_part_of_the_cache_key(tmp_path):
    seen = []

    def fake(system, user, images):
        seen.append(images)
        return "{}"

    llm = LlmClient(Settings(_env_file=None, llm_cache_dir=str(tmp_path)), completer=fake)
    llm.complete("s", "u")
    llm.complete("s", "u", [b"png-1"])
    llm.complete("s", "u", [b"png-1"])                     # cached
    llm.complete("s", "u", [b"png-2"])
    assert seen == [[], [b"png-1"], [b"png-2"]]


def test_a_cv_without_dated_rows_is_noted_not_failed():
    check = experience_check(cv_result([job(None, None)], used="7"), CV_ITEM, AS_OF)
    assert check.passed() and check.value_matches is None and "not recomputed" in check.note
