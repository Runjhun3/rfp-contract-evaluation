-- 018_evidence_check_region: the box on its page that a document check's finding is
-- about (x, y, w, h as fractions of the page from the top left), so the evidence screen
-- can outline it on the bid page (docs/decisions.md D-063). Null for every other check.
alter table evidence_check add column if not exists region jsonb;
