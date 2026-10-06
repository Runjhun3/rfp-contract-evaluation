-- 017_audit_events: who changed the participants and the firm list, who started each
-- job and why, and the criteria as they stood when approved (docs/decisions.md D-054).
-- Append-only, as every audit table (standards rule 10).

-- One row per event. tender_id null: the shared firm list. target is the firm's name
-- at the time, so the event still reads right after a rename or a deletion.
create table if not exists audit_event (
  event_id  bigserial primary key,
  tender_id uuid references tender on delete cascade,
  actor     uuid references app_user,               -- null: the system acted on its own
  action    text not null,
  target    text not null default '',
  details   jsonb not null default '{}',
  at        timestamptz not null default now()
);
create index if not exists audit_event_tender on audit_event (tender_id, at);
create index if not exists audit_event_bidder on audit_event ((details->>'bidder_id'));

-- Whose action queued a job, and which action (e.g. "Bid uploaded").
alter table job add column if not exists created_by uuid references app_user;
alter table job add column if not exists cause text not null default '';

-- The criteria as approved, next to the approved rule text.
alter table evaluation_prompt add column if not exists approved_criteria jsonb;
