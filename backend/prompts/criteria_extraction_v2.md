Below is the full text of an RFP issued on GeM (or one chunk of it).
Find every eligibility criterion and every technical evaluation criterion.

Find them by MEANING, not by heading. They may be called "Annexure III",
"Evaluation Criteria", "Marking scheme", "Technical scoring", "Pre-qualification",
or sit in a table with no heading at all. Ignore clauses that only describe
the process (bid submission steps, payment terms, penalties).

NOT criteria: blank formats and templates the bidder fills in (project detail
sheets, CV formats, declaration or undertaking forms, bank guarantee formats).
A form is only the way to prove a requirement stated elsewhere; never return
a form as a criterion.

REQUIRED DOCUMENTS: a list of documents that must be submitted with the bid
(e.g. "Documents to be submitted") makes each mandatory document an ELIGIBILITY
row (pass/fail, max_marks null), unless the same requirement is already an
eligibility row. Documents listed only as proof for a scored criterion (e.g.
work orders for past projects, CVs) are not separate rows.

For EVERY criterion and sub-criterion return:
- code: technical and presentation criteria as numbered in the RFP (e.g. "A",
  "A.1", "B.2"), or "T.1", "T.2" ... if unnumbered. Eligibility rows are always
  "E.1", "E.2" ... in the order found (their own numbers clash with the
  technical ones).
- parent: the code of the criterion this one is a sub-criterion of (e.g. "A" for
  "A.1", "A.1" for "A.1.a"), or null for a top-level criterion
- stage: ELIGIBILITY (a pass/fail condition, including a required document),
  TECHNICAL (marks given from the bid documents) or PRESENTATION (marks given
  for a presentation or interview, even when the slides come with the bid)
- title: short name
- rfp_text: the clause copied WORD FOR WORD, including its notes
- meaning: one plain sentence saying what a bidder must show to score
  (used to match bid sections that use different wording)
- max_marks: number as string, or null for pass/fail
- max_items: "maximum N projects/CVs considered" as an integer, or null
- kind: PROJECT if marks are given per past project/assignment, CV if marks are
  given per proposed person, else null
- item_marks: every TOTAL one item can earn, as strings (e.g. ["1", "1.5", "2"]
  for value slabs). When an item is scored in parts, list every possible sum of
  its parts, not the parts alone: a CV with a 3-mark part and a 4-mark part can
  earn ["0", "3", "4", "7"]. Else []
- scored_by: COMMITTEE for presentations/interviews, else LLM
- rfp_page: the [PDF p. N] where the clause starts

GROUPS: a criterion that has sub-criteria is a group heading. Return it as its
own row, with max_marks as the RFP states it for the whole group, kind null,
max_items null and item_marks []. Every one of its sub-criteria must name it in
"parent". Never copy a group's marks onto its sub-criteria or add them up; each
row carries only the marks the RFP prints against it.

GENERAL CONDITIONS: a note that applies to several or all criteria (e.g. where
past work must have been executed and in what role, what happens when more CVs
than required are submitted) goes, word for word, into "general_conditions"
once, with its page. Do not copy it into a single criterion's rfp_text.

Do not summarise, interpret or merge clauses in rfp_text. If marks in a table
and in the text disagree, return both in "conflict" and do not choose.

Return exactly this JSON:
{"criteria": [
 {"code": "A", "parent": null, "stage": "TECHNICAL", "title": "...",
  "rfp_text": "...", "meaning": "...", "max_marks": "40", "max_items": null,
  "kind": null, "item_marks": [], "scored_by": "LLM", "rfp_page": 20,
  "conflict": null},
 {"code": "A.1", "parent": "A", "stage": "TECHNICAL", "title": "...",
  "rfp_text": "...", "meaning": "...", "max_marks": "15", "max_items": 5,
  "kind": "PROJECT", "item_marks": ["3"], "scored_by": "LLM", "rfp_page": 20,
  "conflict": null}],
 "general_conditions": [{"text": "...", "rfp_page": 21}]}

PAGES
{{pages}}
