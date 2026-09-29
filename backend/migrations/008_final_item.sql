-- 008_final_item: expose each item's final state (docs/decisions.md, D-037), so the
-- evidence screen groups items by what makes up the final marks, from the same rule
-- final_score totals: an item overridden into the count shows as counted.
--
-- final_item: an item's final marks (its latest decision, else the AI's marks if it
-- was counted, else 0) and whether it is counted: among the best max_items of the
-- criterion with marks above 0. Ties keep the AI's choice first, then page order.
-- final_score: unchanged rule (migration 006), now totalled from final_item.
drop view run_total;
drop view final_score;

create view final_item as
with item_final as (
  select s.score_id, i.item_id, i.from_page, c.max_items,
         coalesce(r.counted, false) as counted_by_ai,
         coalesce(d.final_marks, case when r.counted then r.marks else 0 end) as marks,
         d.review_id is not null as decided
  from criterion_score s
  join criterion c on c.criterion_id = s.criterion_id
  join bid_item i on i.run_id = s.run_id and i.submission_id = s.submission_id
                 and i.criterion_id = s.criterion_id
  left join item_result r on r.item_id = i.item_id
  left join lateral (
    select x.review_id, x.final_marks from review_decision x
    where x.score_id = s.score_id and x.item_id = i.item_id
    order by x.decided_at desc limit 1) d on true
), ranked as (
  select f.*, row_number() over (partition by f.score_id
                                 order by f.marks desc, f.counted_by_ai desc, f.from_page) as n
  from item_final f
)
select score_id, item_id, marks, decided, counted_by_ai,
       marks > 0 and n <= coalesce(max_items, n) as counted
from ranked;

create view final_score as
with per_score as (
  select score_id,
         sum(marks) filter (where counted) as best,
         count(*) as items,
         count(*) filter (where decided) as decided,
         count(*) filter (where counted_by_ai and not decided) as counted_open
  from final_item group by score_id
)
select s.run_id, s.submission_id, s.criterion_id, s.score_id,
       case when last.review_id is not null and last.item_id is null then last.final_marks
            when coalesce(p.decided, 0) > 0
              then least(coalesce(p.best, 0), coalesce(c.max_marks, coalesce(p.best, 0)))
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
