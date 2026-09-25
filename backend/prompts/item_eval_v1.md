Bidder: {{bidder}}
Item: {{label}} ({{kind}})
Submitted under criterion: {{code}}

TASK
1. Read the pages below and extract the facts. For every fact give the
   value, the page and the exact quote it comes from.
2. Decide if this item is eligible under criterion {{code}} and the marks it
   would earn if counted. Do NOT apply "maximum N items" here; that is done later.
3. List in relies_on every fact your decision depends on
   (e.g. ["value_inr", "end_on", "is_completed"]).
4. For a CV: judge each sub-criterion (meeting criteria, prior experience)
   separately, with quotes, and give its marks.

A fact object is: {"value": "...", "page": 306, "quote": "exact words from that page"}
Use null for a fact that is not on the pages.

Return JSON in this shape (the // comments are for you; do not output them):
{
  "label": "{{label}}",
  "code": "{{code}}",
  "facts": {
    "title": fact,
    "client": fact,
    "country": fact,
    "awarded_on": fact,          // value as YYYY-MM-DD
    "start_on": fact,            // value as YYYY-MM-DD
    "end_on": fact,              // value as YYYY-MM-DD
    "value_inr": fact,           // value as plain rupees, e.g. "90600000"
    "is_completed": fact         // value "true" or "false"
  },
  "evidence": {"work_order": [page numbers], "completion_or_ca": [page numbers]},
  "cv": null or {
    "degree": fact,
    "years_experience": fact,
    "sports_or_govt_experience": fact,
    "sub_marks": {"meeting_criteria": "number as string", "prior_experience": "number as string"}
  },
  "relies_on": ["fact names"],
  "eligible": true | false,
  "marks": "number as string (0 if not eligible)",
  "reason": "one sentence",
  "confidence": 0.0-1.0,
  "suspicious_text": [{"page": 0, "quote": "..."}]
}

PAGES
{{pages}}
