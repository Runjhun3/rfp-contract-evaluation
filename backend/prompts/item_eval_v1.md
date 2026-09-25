Bidder: {{bidder}}
Item: {{label}} ({{kind}})
The bidder claims this item under: {{claimed_codes}}

TASK
1. Read the pages below and extract the facts.
2. For EACH criterion code in the claim list above, decide whether this item
   is eligible under that criterion's rules, and the marks it would earn if
   counted. Do not apply "maximum N projects" here: that is done later.
3. For a CV: judge each sub-criterion (meeting criteria, prior experience)
   separately and give its marks.

Return exactly this JSON:
{
  "label": "{{label}}",
  "facts": {
    "client": "string or null",
    "country": "IN or other ISO code or null",
    "awarded_on": "YYYY-MM-DD or null",
    "start_on": "YYYY-MM-DD or null",
    "end_on": "YYYY-MM-DD or null",
    "duration_months": "number as string or null",
    "value_inr": "number as string or null",
    "is_completed": true | false | null,
    "evidence": {"work_order": [page numbers], "completion_or_ca": [page numbers]},
    "cv": {"degree": "...", "years_experience": "...", "sports_or_govt_experience": "..."} or null
  },
  "judgements": [
    {
      "code": "A.2",
      "eligible": true | false,
      "marks": "number as string (0 if not eligible)",
      "reason": "one sentence",
      "evidence_pages": [page numbers],
      "confidence": 0.0-1.0
    }
  ]
}

PAGES
{{pages}}
