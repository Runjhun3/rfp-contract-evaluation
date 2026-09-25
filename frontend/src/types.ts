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
  criterion_id: string; code: string; stage: string; kind: string | null; title: string;
  rfp_text: string; meaning: string; max_marks: Marks | null; max_items: number | null;
  scored_by: string; rfp_page: number | null; allowed: string;
}
export interface Prompt { prompt_id: string; version: number; criteria_block: string; status: string }
export interface CriteriaPage extends Head { criteria: Criterion[]; prompt: Prompt | null; technical_total: Marks }

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
  submission_id: string; name: string; stage: string; rank: string; cells: Record<string, Cell>;
  docs: Marks; presentation: Marks | null; total: Marks;
}
export interface ResultsPage extends Head {
  run: Run; codes: { code: string; max_marks: Marks | null }[]; rows: ResultRow[];
  presentation: { criterion_id: string; code: string; max_marks: Marks | null } | null;
  open_reviews: number; docs_max: Marks;
}

export interface Score {
  score_id: string; run_id: string; submission_id: string; code: string; title: string;
  checked_marks: Marks; max_marks: Marks | null; max_items: number | null; needs_review: boolean;
  review_reasons: string[] | null; summary: string | null; short_name: string;
  final_marks: Marks; reviewed: boolean;
}
export interface Item {
  item_id: string; label: string; title: string | null; from_page: number; to_page: number;
  counted: boolean | null; marks: Marks | null; reason: string | null; count_reason: string | null;
}
export interface Check {
  fact: string; pdf_page_no: number | null; quote: string | null; quote_found: boolean;
  match_score: Marks | null; parsed_value: string | null; value_matches: boolean | null; note: string | null;
}
export interface Decision { action: string; final_marks: Marks; reason: string; full_name: string; decided: string }
export interface EvidencePage {
  score: Score; items: Item[]; item: Item | null; checks: Check[]; history: Decision[]; project: Project;
}
