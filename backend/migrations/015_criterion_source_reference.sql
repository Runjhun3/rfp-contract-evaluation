-- 015_criterion_source_reference: clause/annexure provenance is metadata, never a title.
alter table criterion add column if not exists source_reference text;
