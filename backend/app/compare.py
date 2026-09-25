"""Compare a run's scores with the committee's sheet (tests/golden/.../expected_scores.json)."""
from decimal import Decimal
from pathlib import Path

from app.schemas.llm import CriterionResult
from app.schemas.records import CriterionScore, Item
from app.storage import read, safe_name


def compare(run_dir: Path, expected_path: Path, bidder: str) -> str:
    expected = read(expected_path)["bidders"][bidder]
    scores = [CriterionScore.model_validate(s) for s in read(run_dir / "scores.json")]
    lines = ["| Criterion | Committee | LLM | Python check | Match | Review flags |",
             "| --- | --- | --- | --- | --- | --- |"]
    matched = 0
    for s in scores:
        want = Decimal(expected[s.code]) if s.code in expected else None
        ok = want is not None and s.checked_marks == want
        matched += ok
        lines.append(f"| {s.code} | {want} | {s.llm_marks} | {s.checked_marks} | "
                     f"{'yes' if ok else 'NO'} | {', '.join(s.review_reasons) or '-'} |")
    total = sum((s.checked_marks for s in scores), Decimal(0))
    lines.append(f"| Total /65 | {expected.get('total_65')} | | {total} | | |")
    lines.append(f"\n{matched} of {len(scores)} criteria match the committee.")
    lines += _exclusions(run_dir, expected.get("expect_excluded", {}))
    return "\n".join(lines)


def _exclusions(run_dir: Path, wanted: dict[str, dict[str, str]]) -> list[str]:
    out = []
    titles = {i["label"]: Item.model_validate(i).title.lower() for i in read(run_dir / "items.json")}
    for code, names in wanted.items():
        result = CriterionResult.model_validate(read(run_dir / "criteria" / f"{safe_name(code)}.json"))
        out.append(f"\n### {code}: items the committee excluded")
        for name, why in names.items():
            rows = [r for r in result.items if f"{name.lower()}:" in titles.get(r.label, "")]
            got = "; ".join(f"{r.label} counted={r.counted} ({r.reason})" for r in rows) or "not found"
            out.append(f"- {name} — committee: {why} — LLM: {got}")
    return out
