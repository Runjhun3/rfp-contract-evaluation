Below is the full text of an RFP issued on GeM (or one chunk of it).
Find every eligibility criterion and every technical evaluation criterion.

Find them by MEANING, not by heading. They may be called "Annexure III",
"Evaluation Criteria", "Marking scheme", "Technical scoring", "Pre-qualification",
or sit in a table with no heading at all. Ignore clauses that only describe
the process (bid submission steps, payment terms, penalties).

For EVERY criterion and sub-criterion return:
- code: as numbered in the RFP (e.g. "A", "A.1", "B.2"); if unnumbered, eligibility
  items as "E.1", "E.2" ... and technical items as "T.1", "T.2" ...
- stage: ELIGIBILITY, TECHNICAL or PRESENTATION
- title: short name
- rfp_text: the clause copied WORD FOR WORD, including its notes
- meaning: one plain sentence saying what a bidder must show to score
  (used to match bid sections that use different wording)
- max_marks: number as string, or null for pass/fail
- max_items: "maximum N projects/CVs considered" as an integer, or null
- kind: PROJECT if marks are given per past project/assignment, CV if marks are
  given per proposed person, else null
- item_marks: every mark ONE item can earn, as strings (e.g. ["1", "1.5", "2"]
  for value slabs, ["0", "4", "8"] for a CV with two 4-mark parts), else []
- scored_by: COMMITTEE for presentations/interviews, else LLM
- rfp_page: the [PDF p. N] where the clause starts

Do not summarise, interpret or merge clauses in rfp_text. If marks in a table
and in the text disagree, return both in "conflict" and do not choose.

Return exactly this JSON:
{"criteria": [{"code": "A.1", "parent": "A", "stage": "TECHNICAL", "title": "...",
  "rfp_text": "...", "meaning": "...", "max_marks": "16", "max_items": 8,
  "kind": "PROJECT", "item_marks": ["2"], "scored_by": "LLM", "rfp_page": 34,
  "conflict": null}]}

PAGES
{{pages}}
