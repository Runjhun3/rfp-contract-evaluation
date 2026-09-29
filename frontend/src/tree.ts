// Group headings and their sub-rows on the criteria page. Codes only; no marks maths
// (the API computes group totals and checks).
import type { Criterion } from "./types";

// Codes of the headings above a row, nearest first (A.1.a -> ["A.1", "A"]).
export function ancestors(row: Criterion, rows: Criterion[]): string[] {
  const byCode = new Map(rows.map((r) => [r.code, r]));
  const out: string[] = [];
  let parent = row.parent_code;
  while (parent && byCode.has(parent) && !out.includes(parent)) {
    out.push(parent);
    parent = byCode.get(parent)?.parent_code ?? null;
  }
  return out;
}

export function isUnder(row: Criterion, group: string, rows: Criterion[]): boolean {
  return ancestors(row, rows).includes(group);
}

// The heading's "Scored by": the value all its scored sub-rows share, or MIXED.
export function groupScoredBy(group: string, rows: Criterion[]): string {
  const values = new Set(rows.filter((r) => !r.is_group && isUnder(r, group, rows)).map((r) => r.scored_by));
  return values.size === 1 ? [...values][0] : "MIXED";
}

// Setting a heading's "Scored by" applies it to every row under it.
export function setGroupScoredBy(group: string, value: string, rows: Criterion[]): Criterion[] {
  return rows.map((r) => (r.code === group || isUnder(r, group, rows) ? { ...r, scored_by: value } : r));
}

const CHECKED: (keyof Criterion)[] = ["max_marks", "max_items", "allowed"];

// True when a value behind the heading's total was edited since the page loaded,
// so the total and its check are out of date until the user saves.
export function groupEdited(group: string, rows: Criterion[], saved: Criterion[]): boolean {
  const before = new Map(saved.map((r) => [r.criterion_id, r]));
  return rows
    .filter((r) => r.code === group || isUnder(r, group, rows))
    .some((r) => CHECKED.some((k) => String(r[k] ?? "") !== String(before.get(r.criterion_id)?.[k] ?? "")));
}
