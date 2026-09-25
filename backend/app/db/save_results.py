"""Write a run's items, LLM judgements, Python checks and scores."""
import json
import uuid
from pathlib import Path

from app.schemas.llm import CriterionResult, ItemResult
from app.schemas.records import CopyGroup, CriterionScore, EvidenceCheck, Item
from app.storage import read, safe_name


def save_results(cur, run_dir: Path, run_id: str, submission_id: str,
                 criterion_ids: dict[str, str], items: list[Item]) -> None:
    groups = _save_copy_groups(cur, run_dir, run_id, submission_id)
    item_ids = {i.label: str(uuid.uuid4()) for i in items}
    cur.executemany(
        """insert into bid_item (item_id, run_id, submission_id, criterion_id, label, title, kind,
             map_confidence, from_page, to_page, copy_group_id)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [(item_ids[i.label], run_id, submission_id, criterion_ids[i.criterion_code], i.label,
          i.title, i.kind, i.map_confidence, i.from_page, i.to_page, groups.get(i.label))
         for i in items])
    _save_item_results(cur, run_dir, items, item_ids, _counted(run_dir, criterion_ids))
    _save_checks(cur, run_dir, item_ids)
    _save_scores(cur, run_dir, run_id, submission_id, criterion_ids)


def _save_copy_groups(cur, run_dir: Path, run_id: str, submission_id: str) -> dict[str, str]:
    by_label = {}
    for raw in read(run_dir / "copy_groups.json"):
        group = CopyGroup.model_validate(raw)
        group_id = str(uuid.uuid4())
        cur.execute("""insert into copy_group (copy_group_id, run_id, submission_id, mismatches)
                       values (%s, %s, %s, %s::text[])""",
                    (group_id, run_id, submission_id, group.mismatches))
        by_label.update({label: group_id for label in group.labels})
    return by_label


def _counted(run_dir: Path, criterion_ids: dict[str, str]) -> dict[str, tuple[bool, str]]:
    counted = {}
    for code in criterion_ids:
        path = run_dir / "criteria" / f"{safe_name(code)}.json"
        if path.exists():
            for row in CriterionResult.model_validate(read(path)).items:
                counted[row.label] = (row.counted, row.reason)
    return counted


def _save_item_results(cur, run_dir: Path, items: list[Item], item_ids: dict[str, str],
                       counted: dict[str, tuple[bool, str]]) -> None:
    for item in items:
        path = run_dir / "items" / f"{safe_name(item.label)}.json"
        if not path.exists():
            continue
        r = ItemResult.model_validate(read(path))
        was_counted, count_reason = counted.get(item.label, (None, None))
        cur.execute(
            """insert into item_result (item_id, eligible, marks, counted, count_reason, reason,
                 confidence, relies_on, facts, evidence, cv, suspicious_text)
               values (%s, %s, %s, %s, %s, %s, %s, %s::text[], %s::jsonb, %s::jsonb, %s::jsonb,
                       %s::jsonb)""",
            (item_ids[item.label], r.eligible, r.marks, was_counted, count_reason, r.reason,
             r.confidence, r.relies_on, _json(r.facts), _json(r.evidence),
             _json(r.cv) if r.cv else None, _json(r.suspicious_text)))


def _save_checks(cur, run_dir: Path, item_ids: dict[str, str]) -> None:
    checks = [EvidenceCheck.model_validate(c) for c in read(run_dir / "evidence_checks.json")]
    cur.executemany(
        """insert into evidence_check (item_id, fact, pdf_page_no, quote, quote_found, match_score,
             parsed_value, value_matches, note) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [(item_ids[c.label], c.fact, c.pdf_page_no, c.quote, c.quote_found, c.match_score,
          c.parsed_value, c.value_matches, c.note) for c in checks if c.label in item_ids])


def _save_scores(cur, run_dir: Path, run_id: str, submission_id: str,
                 criterion_ids: dict[str, str]) -> None:
    scores = [CriterionScore.model_validate(s) for s in read(run_dir / "scores.json")]
    cur.executemany(
        """insert into criterion_score (run_id, submission_id, criterion_id, llm_marks,
             checked_marks, arithmetic_ok, needs_review, review_reasons, summary)
           values (%s, %s, %s, %s, %s, %s, %s, %s::text[], %s)""",
        [(run_id, submission_id, criterion_ids[s.code], s.llm_marks, s.checked_marks,
          s.arithmetic_ok, s.needs_review, s.review_reasons, s.summary) for s in scores])


def _json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, dict):
        value = {k: (v.model_dump(mode="json") if hasattr(v, "model_dump") else v)
                 for k, v in value.items()}
    elif isinstance(value, list):
        value = [v.model_dump(mode="json") if hasattr(v, "model_dump") else v for v in value]
    return json.dumps(value, ensure_ascii=False)
