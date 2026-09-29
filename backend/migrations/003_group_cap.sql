-- 003_group_cap: an optional cap on a group heading's marks (docs/decisions.md, D-030).
-- When set, the group's total is min(sum of its sub-criteria, cap); results keep
-- both numbers. Only group headings (rows another row names as parent) use it.
alter table criterion add column if not exists group_cap numeric(6,2)
  check (group_cap is null or group_cap > 0);
