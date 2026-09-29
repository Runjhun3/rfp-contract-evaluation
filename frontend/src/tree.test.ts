import { describe, expect, it } from "vitest";
import { ancestors, groupEdited, groupScoredBy, setGroupScoredBy } from "./tree";
import type { Criterion } from "./types";

const row = (code: string, parent: string | null, is_group = false, scored_by = "LLM"): Criterion => ({
  criterion_id: code, code, parent_code: parent, is_group, stage: "TECHNICAL", kind: null, title: code,
  rfp_text: "", meaning: "", max_marks: "10", max_items: null, scored_by, rfp_page: null, allowed: "",
  group_cap: null,
});

const rows = [row("A", null, true), row("A.1", "A"), row("A.2", "A"), row("B", null, true),
  row("B.1", "B", true), row("B.1.a", "B.1"), row("B.2", "B", false, "COMMITTEE")];

describe("criteria tree", () => {
  it("finds every heading above a row", () => {
    expect(ancestors(rows[5], rows)).toEqual(["B.1", "B"]);
    expect(ancestors(rows[0], rows)).toEqual([]);
  });

  it("shows a shared Scored by, or Mixed when sub-rows differ", () => {
    expect(groupScoredBy("A", rows)).toBe("LLM");
    expect(groupScoredBy("B", rows)).toBe("MIXED");
  });

  it("applies a heading's Scored by to all rows under it, at any depth", () => {
    const next = setGroupScoredBy("B", "COMMITTEE", rows);
    expect(groupScoredBy("B", next)).toBe("COMMITTEE");
    expect(next.find((r) => r.code === "A.1")?.scored_by).toBe("LLM");
  });

  it("notices when a value behind a heading's total was edited", () => {
    const edited = rows.map((r) => (r.code === "A.2" ? { ...r, max_marks: "12" } : r));
    expect(groupEdited("A", edited, rows)).toBe(true);
    expect(groupEdited("B", edited, rows)).toBe(false);
  });
});
