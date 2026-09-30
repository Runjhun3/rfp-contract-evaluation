-- 013_rfp_number: the number or letter an RFP itself prints for an eligibility criterion
-- or required document ("3", "B", "II.4"), shown to the committee in place of the
-- internal code (E.1, D.1), which stays the key because RFP numbers clash across lists
-- (docs/decisions.md, D-047). Null when the RFP numbers nothing; the code is shown then.
alter table criterion add column if not exists rfp_no text;
