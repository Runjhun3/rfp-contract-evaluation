from decimal import Decimal

from app.evaluate.arithmetic_check import check_criterion
from app.evaluate.count_bands import band_marks, describe
from app.evaluate.criterion_eval import evaluate_criterion
from app.jobs.handlers import _bands
from app.review import item_limit, override_problem
from app.schemas.llm import ItemResult
from app.schemas.records import CountBand, Criterion

D = Decimal
BANDS = [CountBand(min=1, max=3, marks=D(5)), CountBand(min=4, max=6, marks=D(7)),
         CountBand(min=7, max=None, marks=D(10))]
BY_COUNT = Criterion(code="A.4", title="t", meaning="m", kind="PROJECT", max_marks=D(10),
                     allowed_item_marks=[], count_bands=BANDS)


def item(n, qualifies=True):
    return ItemResult(label=f"A.4 p.{n}", code="A.4", eligible=qualifies,
                      marks=D(1 if qualifies else 0), reason="r", confidence=0.9)


def test_the_band_follows_the_number_of_qualifying_items():
    assert [band_marks(BANDS, n) for n in (0, 1, 3, 4, 6, 7, 12)] == \
        [0, 5, 5, 7, 7, 10, 10]
    assert describe(BANDS) == "1-3: 5; 4-6: 7; 7 or more: 10"


def test_a_count_based_criterion_is_totalled_in_python_without_an_llm_call():
    results = [item(n) for n in range(1, 6)] + [item(6, qualifies=False)]
    result = evaluate_criterion(BY_COUNT, "B", results, llm=None)      # no LLM needed
    assert result.counted_items == 5 and result.marks == D(7)
    assert [i.counted for i in result.items] == [True] * 5 + [False]
    assert check_criterion(BY_COUNT, result, {r.label: r for r in results}).ok


def test_the_arithmetic_check_catches_a_wrong_band_or_per_item_marks():
    results = [item(n) for n in range(1, 5)]
    result = evaluate_criterion(BY_COUNT, "B", results, llm=None)
    wrong_total = result.model_copy(update={"marks": D(10)})
    assert "counted items give 7" in check_criterion(
        BY_COUNT, wrong_total, {r.label: r for r in results}).issues[0]
    two_marks = [r.model_copy(update={"marks": D(2)}) for r in results]
    rows = [i.model_copy(update={"marks": D(2)}) for i in result.items]
    issues = check_criterion(BY_COUNT, result.model_copy(update={"items": rows}),
                             {r.label: r for r in two_marks}).issues
    assert any("2 is not an allowed mark ['1']" in i for i in issues)


def test_overrides_under_a_count_based_criterion_are_counts_or_not():
    score = {"count_bands": [{"min": 1, "max": 3, "marks": "5"}], "max_marks": D(10)}
    assert item_limit(score) == D(1)
    assert override_problem(D(1), score, True) is None
    assert override_problem(D("0.5"), score, True).startswith("This criterion counts")


def test_extracted_bands_are_kept_only_when_well_formed():
    good = [{"min": 1, "max": 3, "marks": "5"}, {"min": 4, "max": None, "marks": "7"}]
    assert _bands(good) == [{"min": 1, "max": 3, "marks": "5"},
                            {"min": 4, "max": None, "marks": "7"}]
    assert _bands([{"min": "one", "marks": "5"}]) == []
