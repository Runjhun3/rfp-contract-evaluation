Below are pages from an RFP issued on GeM. Find the eligibility criteria and
the technical evaluation criteria (usually "Annexure III"), and the list of
documents to be submitted (usually "Annexure II").

For EVERY criterion and sub-criterion return:
- code exactly as in the RFP (e.g. "A", "A.1", "B.2"); eligibility items as "E.1", "E.2" ...
- stage: ELIGIBILITY, TECHNICAL or PRESENTATION
- title: short name
- rfp_text: the clause copied WORD FOR WORD, including its notes
- max_marks: number as string, or null for pass/fail
- max_items: "maximum N projects/CVs considered", as an integer, or null
- scored_by: COMMITTEE for presentations/interviews, else LLM
- rfp_page: the [PDF p. N] where the clause starts

Do not summarise, interpret or merge clauses. If marks in a table and in the
text disagree, return both in a "conflict" field and do not choose.

Return exactly this JSON:
{"criteria": [{"code": "A.1", "parent": "A", "stage": "TECHNICAL", "title": "...",
  "rfp_text": "...", "max_marks": "16", "max_items": 8, "scored_by": "LLM",
  "rfp_page": 34, "conflict": null}]}

PAGES
{{pages}}
