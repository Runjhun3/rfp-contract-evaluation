Bidder: {{bidder}}
Item: {{label}} ({{kind}})
Submitted under criterion: {{code}}

CRITERION {{code}} AS THE RFP STATES IT
{{rfp_text}}

An item of kind BID is the bidder as a whole: the pages below are all the evidence
the bid gives for a criterion scored once per bidder (e.g. turnover, net worth, a
certification). Put the figures the criterion needs in facts (one fact per figure,
e.g. turnover per year), list the tests in conditions, and score the bidder.

CLAIMS AND EVIDENCE
The firm's own pages (its claim table, project profile, summary or covering note) are
claims. The documents the RFP names as proof (e.g. work order, contract, completion or
CA certificate) are the evidence: take every fact from them and quote them. Where the
RFP accepts a document the firm signs itself (e.g. a declaration), that document is
the evidence.

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
5. If eligible = false, name the hard fail in hard_fail. It is exactly one of:
   - "missing_document": a document the RFP requires is not on these pages
   - "failed_test": a test in conditions is not met; give its fact
   - "rfp_exclusion": the RFP expressly excludes this item (e.g. a CV proposed
     for a different position); copy the RFP's words into rfp_quote
   A doubt about a category, type or relevance is never a hard fail: mark the
   item eligible, confidence below 0.8, and say what the committee must decide.
   Software checks that every rejection has a hard fail. If eligible = true,
   hard_fail is null.
6. For a CV:
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
7. certificate_on: the date printed on the completion or CA certificate (the date it
   was issued, not a date it mentions), or null when there is none.
8. discrepancies: every fact on which the firm's own page and a document state
   different values (e.g. the claim table gives one contract value and the
   certificate another). Give the claim and the document each as a fact with its
   page and exact quote. Leave the list empty when they agree.
9. references: every document that one of the item's documents refers to (e.g. "in
   accordance with the extension letter dated 15.03.2022", an amendment, an earlier
   order), with the page and exact words that refer to it, and found_on_page: the
   page among those below where that document is, or null if it is not there.
10. sums: every total or average a document states that is made of other figures
   on the pages (e.g. an average turnover over three years). Put the stated result
   and each figure in facts (amounts as plain rupees, names ending in _inr) and list
   {"result": stated fact name, "op": "sum" or "average", "parts": [fact names]}.
   Software recomputes each one.

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
    "is_completed": fact,        // value "true" or "false"
    "certificate_on": fact       // value as YYYY-MM-DD; add any other figure you use
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
  "hard_fail": null or {"kind": "...", "detail": "one sentence", "fact": null,
                        "rfp_quote": null},
  "eligible": true | false,
  "marks": "number as string (0 if not eligible)",
  "reason": "one sentence",
  "confidence": 0.0-1.0,
  "suspicious_text": [{"page": 0, "quote": "..."}],
  "discrepancies": [{"about": "contract value", "claim": fact, "document": fact}],
  "references": [{"document": "...", "page": 0, "quote": "...", "found_on_page": null}],
  "sums": [{"result": "fact name", "op": "average", "parts": ["fact names"]}]
}

PAGES
{{pages}}
