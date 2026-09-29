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
4. List in conditions EVERY numeric or date test you applied from the RFP text,
   one test per entry: minimum or maximum values, value bands, minimum
   duration, award or completion cut-off dates, minimum years of experience.
   For marks that depend on a band, list the test at each band boundary you
   considered (e.g. both "value > 2 crore" and "value > 5 crore").
   - fact: the fact whose value is tested (a fact name used above, a name in
     cv.facts, "duration_months" or "experience_years")
   - test: one of >, >=, <, <=, =
   - threshold: a plain number in the fact's unit (rupees, months, years) or
     a date as YYYY-MM-DD
   - met: your result
   Software recomputes every test from the fact values and checks your result.
5. For a CV:
   a. List every row of the employment record in "employment", in the CV's
      order, with start and end as YYYY-MM ("present" if ongoing) and the
      row's exact words as quote.
   b. experience_years = the total professional experience you used for your
      decision, as a plain number. Base it on the employment rows; if a total
      stated in the CV disagrees with the rows, rely on the rows and say so.
      Software re-adds the rows and flags any difference.
   c. Score every sub-criterion the RFP defines for this position separately
      in sub_scores, named as the RFP names it (e.g. "Meeting criteria"), each
      with its marks and one-sentence reason. A sub-criterion that is not met
      scores 0 there. Put any other fact a sub-criterion needs (e.g. years in
      a sector) in cv.facts and list its name in relies_on.
   d. marks = the sum of sub_scores. eligible = false only when the CV cannot
      be considered at all (e.g. proposed for a different position, or the RFP
      excludes it); an unmet sub-criterion does not make the CV ineligible.

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
    "stated_experience": fact,   // total experience as the CV states it, or null
    "employment": [{"organisation": "...", "role": "...", "start": "YYYY-MM",
                    "end": "YYYY-MM or present", "page": 0, "quote": "..."}],
    "experience_years": "number as string",
    "facts": {"fact name": fact},
    "sub_scores": [{"name": "...", "marks": "number as string", "reason": "..."}]
  },
  "relies_on": ["fact names"],
  "conditions": [{"fact": "value_inr", "test": ">", "threshold": "50000000", "met": true}],
  "eligible": true | false,
  "marks": "number as string (0 if not eligible)",
  "reason": "one sentence",
  "confidence": 0.0-1.0,
  "suspicious_text": [{"page": 0, "quote": "..."}]
}

PAGES
{{pages}}
