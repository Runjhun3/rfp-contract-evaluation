-- 012_required_documents: documents every bid must include (e.g. a signed bid form, a
-- power of attorney) are their own stage, apart from eligibility (docs/decisions.md,
-- D-046). Both are checked by the AI and decided by the committee; only an eligibility
-- criterion decided as not met disqualifies, a missing document is flagged.
alter table criterion drop constraint if exists criterion_stage_check;
alter table criterion add constraint criterion_stage_check
  check (stage in ('ELIGIBILITY','DOCUMENT','TECHNICAL','PRESENTATION'));
