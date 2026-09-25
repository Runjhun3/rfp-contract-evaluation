Below are the item results for criterion {{code}} for bidder {{bidder}}.
Max items: {{max_items}}. Max marks: {{max_marks}}.

RULES
1. Take only items with eligible = true.
2. If there are more eligible items than max items, keep those giving the
   highest marks. On a tie, keep the one listed first by the bidder
   (lower "order").
3. Set counted = true for kept items. Set counted = false for the rest, with
   reason "Beyond maximum of {{max_items}} items".
4. Items with eligible = false stay counted = false with their own reason.
5. List every item before giving the total.
6. Marks = sum of counted item marks, never above {{max_marks}}.

Return exactly this JSON:
{
  "code": "{{code}}",
  "items": [
    {"label": "...", "order": 1, "eligible": true, "counted": true,
     "marks": "2", "reason": "..."}
  ],
  "counted_items": 0,
  "marks": "number as string",
  "summary": "one sentence, e.g. '6 of 11 projects counted x 2 marks'"
}

ITEM RESULTS
{{item_results}}
