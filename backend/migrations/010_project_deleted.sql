-- 010_project_deleted: deleting a project hides it; nothing is removed (docs/decisions.md,
-- D-043). Its bids, runs, scores and committee decisions stay on record (coding
-- standards rule 10: scores and decisions are never deleted); the project simply no
-- longer appears on any page.
alter table tender add column if not exists deleted_at timestamptz;
alter table tender add column if not exists deleted_by uuid references app_user;
