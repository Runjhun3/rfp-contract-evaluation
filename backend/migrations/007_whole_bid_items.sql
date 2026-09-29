-- 007_whole_bid_items: a criterion with marks that is scored neither per project nor
-- per CV (e.g. average annual turnover) is scored once on the whole bid
-- (docs/decisions.md, D-036). Its evidence pages form one item of kind BID.
alter table bid_item drop constraint bid_item_kind_check;
alter table bid_item add constraint bid_item_kind_check check (kind in ('PROJECT', 'CV', 'BID'));
