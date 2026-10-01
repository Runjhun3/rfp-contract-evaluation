-- 014_unified_eligibility: every screened RFP row is an eligibility criterion.
-- A committee can exclude an extracted row before approval; excluded rows are never
-- labelled, checked, displayed in later stages, or used for qualification.
alter table criterion add column if not exists considered boolean not null default true;
alter table criterion add column if not exists classification_unsure boolean not null default false;

update criterion set stage = 'ELIGIBILITY' where stage = 'DOCUMENT';

alter table criterion drop constraint if exists criterion_stage_check;
alter table criterion add constraint criterion_stage_check
  check (stage in ('ELIGIBILITY','TECHNICAL','PRESENTATION'));
