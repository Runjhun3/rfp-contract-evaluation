-- 006_item_decisions: the committee decides each item (project or CV), not only the
-- whole criterion (docs/decisions.md, D-034).
--
-- 1. A reason is needed to override, not to accept the AI's marks.
alter table review_decision drop constraint review_decision_reason_check;
alter table review_decision alter column reason set default '';
alter table review_decision add constraint review_decision_reason_check
  check (action = 'ACCEPT' or length(trim(reason)) >= 10);

-- 2. Final marks per criterion score.
--    An item's final mark: its latest decision's marks, else the AI's marks if it was
--    counted, else 0. The criterion's final: the best max_items of those, capped at
--    max_marks. A criterion-level decision (item_id null) wins while it is the latest
--    decision on the score, so earlier whole-criterion decisions keep their effect.
--    Reviewed: the latest decision is criterion-level, or items exist, at least one is
--    decided and every counted item is decided.
drop view run_total;
drop view final_score;

create view final_score as
with item_final as (
  select s.score_id, i.item_id, coalesce(r.counted, false) as counted,
         coalesce(d.final_marks, case when r.counted then r.marks else 0 end) as marks,
         d.review_id is not null as decided
  from criterion_score s
  join bid_item i on i.run_id = s.run_id and i.submission_id = s.submission_id
                 and i.criterion_id = s.criterion_id
  left join item_result r on r.item_id = i.item_id
  left join lateral (
    select x.review_id, x.final_marks from review_decision x
    where x.score_id = s.score_id and x.item_id = i.item_id
    order by x.decided_at desc limit 1) d on true
), ranked as (
  select f.*, row_number() over (partition by f.score_id order by f.marks desc, f.item_id) as n
  from item_final f
), per_score as (
  select r.score_id,
         sum(r.marks) filter (where r.n <= coalesce(c.max_items, r.n)) as best,
         count(*) as items,
         count(*) filter (where r.decided) as decided,
         count(*) filter (where r.counted and not r.decided) as counted_open
  from ranked r
  join criterion_score s on s.score_id = r.score_id
  join criterion c on c.criterion_id = s.criterion_id
  group by r.score_id
)
select s.run_id, s.submission_id, s.criterion_id, s.score_id,
       case when last.review_id is not null and last.item_id is null then last.final_marks
            when coalesce(p.decided, 0) > 0 then least(p.best, coalesce(c.max_marks, p.best))
            else s.checked_marks end as marks,
       s.needs_review,
       (last.review_id is not null and last.item_id is null)
         or (coalesce(p.items, 0) > 0 and p.decided > 0 and p.counted_open = 0) as reviewed,
       last.reason as review_reason
from criterion_score s
join criterion c on c.criterion_id = s.criterion_id
left join per_score p on p.score_id = s.score_id
left join lateral (
  select d.review_id, d.item_id, d.final_marks, d.reason from review_decision d
  where d.score_id = s.score_id order by d.decided_at desc limit 1) last on true;

create view run_total as
select f.run_id, f.submission_id,
       sum(f.marks) as document_marks,
       coalesce((select sum(m.marks) from manual_score m
                 where m.submission_id = f.submission_id), 0) as presentation_marks,
       bool_or(f.needs_review and not f.reviewed) as open_reviews
from final_score f group by f.run_id, f.submission_id;
