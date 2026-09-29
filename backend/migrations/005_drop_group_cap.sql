-- 005_drop_group_cap: the group cap feature is removed (docs/decisions.md, D-033).
-- A group heading's total is again the plain sum of its sub-criteria.
alter table criterion drop column if exists group_cap;
