// Shapes of the project's records and the accounts, as the Python API returns them:
// the activity log, the committee's decisions and the named accounts.
import type { Head } from "./types";

// Account changes on the Users page: what changed (code: the account; old: details).
export interface HistoryRow { stamp: string; who: string | null; what: string; code: string | null; old: string | null; new: string | null }
// The activity log (app/audit_view.py): one action a person took; never the AI's or the
// worker's. project: null for accounts and sign-ins. One page at a time, newest first.
export interface ActivityRow { stamp: string; who: string; area: string; what: string; project: string | null; details: string | null }
// who / since / until: the filters in force (an account's id; YYYY-MM-DD dates, both included).
export interface ActivityLog {
  rows: ActivityRow[]; page: number; pages: number; total: number; category: string | null; categories: { key: string; label: string }[];
  who: string | null; since: string | null; until: string | null; people: { user_id: string; name: string }[];
}
// approved_criteria: each field as the trail shows it; null when approved before they were kept.
type ApprovedCriterion = { code: string; title: string | null; stage: string | null; max_marks: string | null; scored_by: string | null; considered: string | null };
export interface Approval { version: number; full_name: string | null; stamp: string; approved_criteria: ApprovedCriterion[] | null }
export interface AuditPage extends Head, ActivityLog { approvals: Approval[] }
// The committee's decisions, firm by firm (newest first). tone: kept what the AI said, or not.
export interface DecisionRow {
  stamp: string; who: string; area: string; criterion: string; code: string; decision: string; value: string | null;
  ai: string | null; reason: string | null; tone: "accepted" | "overridden" | null;
}
// summary: "12 accepted · 1 overridden · 3 eligibility"; criteria: for the filter, in code order.
export interface DecisionsPage extends Head {
  firms: { firm: string; summary: string; rows: DecisionRow[] }[]; criteria: { code: string; label: string }[];
}

// Named sign-in accounts (administrators only); the .env administrator is not listed.
export interface UserRow {
  user_id: string; username: string; full_name: string; role: string; role_label: string; is_active: boolean; created: string; created_by: string | null;
}
export interface UsersPage { users: UserRow[]; roles: { key: string; label: string }[]; events: HistoryRow[] }
