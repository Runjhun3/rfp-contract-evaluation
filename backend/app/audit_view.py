"""What the project's records show on screen (docs/decisions.md D-057, D-058). Read-only.

- decision_log: the decisions where the committee went against the AI, firm by firm,
  newest first: marks overridden, and eligibility decided otherwise than the AI found.
  Every account may see it; the activity log keeps every decision.
- activity: every action a person took (never the AI's or the worker's), one page at a
  time: for one project, or everywhere (the central log, with accounts and sign-ins).
  With the criteria as approved. Administrators only.
"""
from datetime import date
from uuid import UUID

from app.db import q_activity, q_audit, q_prompts

PROJECT_AREAS = ["PROJECT", "CRITERIA", "PARTICIPANTS", "EVALUATION", "EXPORTS"]
WORD = {"ACCEPT": "AI marks accepted", "OVERRIDE": "Marks overridden",
        "MARKS": "Marks entered", "MET": "Met", "NOT_MET": "Not met", "UNSURE": "Unsure"}


def decision_log(cur, tender_id: str) -> dict:
    """{firms: [{firm, summary, rows}] in firm order, criteria: [{code, label}]} for the
    criterion filter: only overrides, i.e. rows whose tone is "overridden" (accepting
    the AI, committee-entered marks and decisions on AI-unsure checks are left out).
    Each row: stamp, who, area, criterion, code, decision, value, ai, reason, tone."""
    firms: dict[str, list[dict]] = {}
    criteria: dict[str, str] = {}
    for d in q_audit.committee_decisions(cur, tender_id):
        row = _decision(d)
        if row["tone"] != "overridden":
            continue
        firms.setdefault(d["firm"], []).append(row)
        criteria[d["code"]] = d["code_label"]
    return {"firms": [{"firm": firm, "summary": _summary(rows), "rows": rows}
                      for firm, rows in firms.items()],
            "criteria": [{"code": c, "label": criteria[c]} for c in sorted(criteria, key=_order)]}


def _order(code: str) -> list:
    """A.2 before A.10; screened rows (E.1 …) after the scored ones."""
    parts = [int(p) if p.isdigit() else p for p in code.split(".")]
    return [code.startswith("E."), *[(0, p) if isinstance(p, int) else (1, p) for p in parts]]


def _summary(rows: list[dict]) -> str:
    """"8 marks overridden · 1 eligibility result overridden" for a firm."""
    marks = sum(r["area"] == "Marks" for r in rows)
    checks = sum(r["area"] == "Eligibility" for r in rows)
    counts = [(marks, "mark" if marks == 1 else "marks"),
              (checks, "eligibility result" if checks == 1 else "eligibility results")]
    return " · ".join(f"{n} {label} overridden" for n, label in counts if n)


def _decision(d: dict) -> dict:
    eligibility = d["area"] == "Eligibility"
    if d["kind"] in ("ACCEPT", "OVERRIDE"):
        tone = "accepted" if d["kind"] == "ACCEPT" else "overridden"
    elif eligibility and d["ai"] != "UNSURE":
        tone = "accepted" if d["kind"] == d["ai"] else "overridden"
    else:
        tone = None
    return {"stamp": d["stamp"], "who": d["who"], "area": d["area"],
            "criterion": d["criterion"], "code": d["code"], "decision": WORD[d["kind"]],
            "value": None if eligibility else d["value"],
            "ai": WORD.get(d["ai"], d["ai"]).lower() if eligibility and d["ai"] else d["ai"],
            "reason": d["reason"], "tone": tone}


def wanted(query, tender_id: str | None) -> dict:
    """What an activity log was asked for (?category=&who=&since=&until=&page=). A value
    that is not an area, an account id or a YYYY-MM-DD date is ignored, not refused."""
    areas = PROJECT_AREAS if tender_id else list(q_activity.CATEGORIES)
    category = query.get("category") if query.get("category") in areas else None
    page = query.get("page", "1")
    return {"category": category, "categories": [category] if category else areas,
            "areas": areas, "who": _uuid(query.get("who")), "since": _day(query.get("since")),
            "until": _day(query.get("until")), "page": max(1, int(page)) if page.isdigit() else 1}


def _uuid(value: str | None) -> str | None:
    try:
        return str(UUID(value)) if value else None
    except ValueError:
        return None


def _day(value: str | None) -> str | None:
    try:
        return date.fromisoformat(value).isoformat() if value else None
    except ValueError:
        return None


def activity(cur, tender_id: str | None, filters: dict) -> dict:
    """One page of the actions people took: on one project (its areas only; the
    committee's decisions have their own page), or everywhere when tender_id is None."""
    total = q_activity.count(cur, tender_id, filters)
    pages = max(1, -(-total // q_activity.PAGE_SIZE))         # rounded up; 1 when empty
    page = min(filters["page"], pages)                          # past the end: the last page
    return {"rows": activity_rows(cur, tender_id, filters, page),
            "page": page, "pages": pages, "total": total,
            "category": filters["category"], "who": filters["who"],
            "since": filters["since"], "until": filters["until"],
            "categories": [{"key": k, "label": q_activity.CATEGORIES[k]}
                           for k in filters["areas"]],
            "people": q_activity.people(cur)}


def activity_rows(cur, tender_id: str | None, filters: dict, page: int | None) -> list[dict]:
    """The matching actions with their area's name: one page, or all (page None)."""
    return [{**r, "area": q_activity.CATEGORIES[r["category"]]}
            for r in q_activity.actions(cur, tender_id, filters, page)]


def approvals(cur, tender_id: str) -> list[dict]:
    """The criteria as each version was approved, newest first."""
    return list(reversed(q_prompts.approvals(cur, tender_id)))
