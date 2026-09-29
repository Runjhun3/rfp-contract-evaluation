-- 009_count_bands: criteria that give marks by HOW MANY qualifying items the bidder
-- shows, not per item (docs/decisions.md, D-039), e.g. "up to 3 projects - 5 marks,
-- 4-6 projects - 7 marks, 7 or more - 10 marks".
--
-- criterion.count_bands: [{"min": 1, "max": 3, "marks": 5}, ..., {"min": 7, "max": null,
-- "marks": 10}]; empty for criteria scored per item. Each item of such a criterion
-- scores 1 if it qualifies, 0 if not; the criterion's marks are the band that the
-- number of counted items falls in (0 when it falls in none).
alter table criterion add column if not exists count_bands jsonb not null default '[]';

drop view run_total;
drop view final_score;
drop view final_item;

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
         count(*) filter (where counted) as counted_items,
         count(*) as items,
         count(*) filter (where decided) as decided,
         count(*) filter (where counted_by_ai and not decided) as counted_open
  from final_item group by score_id
), totals as (
  select p.*, s.score_id as sid,
         case when jsonb_array_length(c.count_bands) > 0 then coalesce(
                (select (b ->> 'marks')::numeric from jsonb_array_elements(c.count_bands) b
                 where p.counted_items >= (b ->> 'min')::int
                   and (b ->> 'max' is null or p.counted_items <= (b ->> 'max')::int)
                 order by (b ->> 'min')::int desc limit 1), 0)
              else least(coalesce(p.best, 0), coalesce(c.max_marks, coalesce(p.best, 0)))
         end as item_marks
  from per_score p
  join criterion_score s on s.score_id = p.score_id
  join criterion c on c.criterion_id = s.criterion_id
)
select s.run_id, s.submission_id, s.criterion_id, s.score_id,
       case when last.review_id is not null and last.item_id is null then last.final_marks
            when coalesce(t.decided, 0) > 0 then t.item_marks
            else s.checked_marks end as marks,
       s.needs_review,
       (last.review_id is not null and last.item_id is null)
         or (coalesce(t.items, 0) > 0 and t.decided > 0 and t.counted_open = 0) as reviewed,
       last.reason as review_reason
from criterion_score s
left join totals t on t.sid = s.score_id
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
