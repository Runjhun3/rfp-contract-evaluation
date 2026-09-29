// Shapes returned by the Python API (/api/v1). Marks are exact strings, never numbers.
export type Marks = string;

export interface Step { n: number; key: string; label: string; url: string | null; done: boolean; current: boolean }
export interface Project {
  tender_id: string; name: string; gem_bid_no: string | null; department: string | null;
  status: string; bid_due_date: string; due: string;
}
export interface Head { project: Project; steps: Step[] }

export interface ProjectRow {
  tender_id: string; name: string; gem_bid_no: string | null; status: string; due: string;
  participants: number; open_reviews: number; created: string;
}
export interface ProjectList { projects: ProjectRow[]; page: number; more: boolean }

export interface Rfp { doc_id: string; file_name: string; page_count: number; uploaded: string }
export interface RfpPage extends Head { rfp: Rfp | null }

export interface Criterion {
  criterion_id: string; code: string; parent_code: string | null; is_group: boolean; stage: string; kind: string | null; title: string;
  rfp_text: string; meaning: string; max_marks: Marks | null; max_items: number | null;
  scored_by: string; rfp_page: number | null; allowed: string;
  // Group headings only, computed by the API from the saved rows:
  parts?: Marks[]; parts_total?: Marks; rfp_matches?: boolean | null;
  // Scored rows only: set when max items × top mark per item differs from the marks.
  items_warning?: string | null;
}
export interface Prompt { prompt_id: string; version: number; criteria_block: string; status: string }
export interface CriteriaPage extends Head {
  criteria: Criterion[]; prompt: Prompt | null; technical_total: Marks;
}

export interface Firm { bidder_id: string; legal_name: string; short_name: string }
export interface Submission {
  submission_id: string; bidder_id: string; short_name: string; legal_name: string;
  file_id: string | null; file_name: string | null; page_count: number | null; uploaded: string | null;
}
export interface ParticipantsPage extends Head {
  submissions: Submission[]; firms: Firm[]; ready: number; approved: boolean;
}

export interface Run {
  run_id: string; tender_id: string; status: string; model: string; started: string; prompt_version: number;
}
export interface ProgressRow {
  submission_id: string; short_name: string; stage: string; label: string; percent: number; error: string | null;
}
export interface RunPage extends Head { run: Run; rows: ProgressRow[] }

export interface Cell { score_id: string; code: string; marks: Marks; needs_review: boolean; reviewed: boolean }
export interface ResultRow {
  // The participant's latest evaluation. rank, docs and total stay null until it is DONE;
  // status says why (being evaluated, failed, not evaluated yet), null once DONE.
  submission_id: string; name: string; included: boolean; stage: string; status: string | null; rank: string | null;
  // manual: marks the committee entered, by committee-scored criterion id (null = not yet).
  cells: Record<string, Cell>; docs: Marks | null; manual: Record<string, Marks | null>; total: Marks | null;
}
export interface ResultsPage extends Head {
  codes: { code: string; max_marks: Marks | null }[]; rows: ResultRow[];
  committee: { criterion_id: string; code: string; title: string; max_marks: Marks }[]; // committee-scored
  open_reviews: number; docs_max: Marks; committee_max: Marks; evaluating: number; pending: number; ready: boolean;
  export_blockers: string[]; // why the sheet cannot be exported yet; empty when it can
}

export interface Score {
  score_id: string; run_id: string; tender_id: string; submission_id: string; code: string; title: string;
  checked_marks: Marks; max_marks: Marks | null; max_items: number | null; needs_review: boolean;
  review_reasons: string[] | null; summary: string | null; short_name: string;
  final_marks: Marks; reviewed: boolean;
}
// The evidence screen: the API decides what needs attention and words every check.
// marks: the item's final marks (the committee's decision, else the AI's if counted).
export interface ItemRow {
  item_id: string; title: string; pages: string; marks: Marks | null; attention: boolean;
  decision: "ACCEPT" | "OVERRIDE" | null;
}
export interface ItemGroup { key: string; label: string; items: ItemRow[] }
export interface Verdict {
  item_id: string; title: string; pages: string; from_page: number;
  status: "counted" | "not_counted" | "not_scored"; marks: Marks | null; confidence: number | null;
  reason: string; judgement_call: boolean; ai_marks: Marks; counted_by_ai: boolean;
  count_based: boolean; // the criterion gives marks by how many items qualify: 1 = qualifies
  item_limit: Marks; // the most an override can give this item (1 = counts, for a count-based criterion)
  decision: { action: "ACCEPT" | "OVERRIDE"; final_marks: Marks; reason: string } | null;
}
export interface CheckView {
  label: string; detail: string; quote: string | null; page: number | null; state: "problem" | "note" | "passed";
}
export interface EvidencePage {
  score: Score; groups: ItemGroup[]; item: Verdict | null; checks: CheckView[];
  progress: { items: number; counted: number; decided: number };
  project: Project;
}
