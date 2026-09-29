-- 004_participant_included: unticking a participant must not delete it. A submission
-- row carries its bid file and, through runs, every score and committee decision
-- (on delete cascade), so it is switched off instead and can be ticked back on.
alter table bid_submission add column if not exists included boolean not null default true;
