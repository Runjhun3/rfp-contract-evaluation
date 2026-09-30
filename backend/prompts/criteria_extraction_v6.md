Below is the full text of an RFP issued on GeM (or one chunk of it).
Find every eligibility criterion, every document every bid must include, and
every technical evaluation criterion.

Find them by MEANING, not by heading. They may be called "Annexure III",
"Evaluation Criteria", "Marking scheme", "Technical scoring", "Pre-qualification",
or sit in a table with no heading at all. Ignore clauses that only describe
the process (bid submission steps, payment terms, penalties).

NOT criteria: blank formats and templates the bidder fills in (project detail
sheets, CV formats, declaration or undertaking forms, bank guarantee formats).
A form is only the way to prove a requirement stated elsewhere; never return
a form as a criterion.

ELIGIBILITY vs REQUIRED DOCUMENTS: an ELIGIBILITY row is a condition the RFP
itself states as eligibility, pre-qualification or qualification, i.e. one a
bidder must meet to be evaluated at all (e.g. a condition on who may bid, a
bid security, an empanelment, a minimum turnover, a declaration the
eligibility criteria require). A DOCUMENT row is a document every bid must
include that the RFP lists for submission (e.g. under "general documents") but
does not state as an eligibility or pre-qualification condition (e.g. a signed
bid form, a power of attorney, an acceptance of terms). A document listed as
the proof of an eligibility condition is that condition's proof, not a
DOCUMENT row.

NOT APPLICABLE: a document or criterion the RFP marks as not applicable (e.g.
its annexure reads "Not Applicable") is not returned at all.

ELIGIBILITY AND ITS PROOF: an RFP often states a pass/fail requirement in one
place (e.g. an eligibility or pre-qualification table) and names the documents
that prove it in another (e.g. a "Documents to be submitted" list), sometimes
pages apart. Match them by MEANING and return ONE eligibility row per
requirement, with:
- rfp_text: the requirement itself, word for word, together with every
  condition that defines it, wherever the RFP spells those conditions out
  (e.g. a list of what makes a bidder a "fit and proper person", or the format
  a declaration must follow). Never stop at a heading such as "the criteria
  mentioned below": copy the list that follows.
- proof: the documents the RFP asks for to prove this requirement, copied word
  for word from wherever the RFP lists them, or null if the RFP names none.
EVERY MANDATORY DOCUMENT: every mandatory document in a list of documents to
submit with the bid must end up in some row: as the proof of the eligibility
condition it proves, or as its own DOCUMENT row. A DOCUMENT row's rfp_text is
the list entry word for word, proof null. Documents listed only as proof for a
scored criterion (e.g. work orders for past projects, CVs, presentation
slides) are neither.

For EVERY criterion and sub-criterion return:
- code: technical and presentation criteria as numbered in the RFP (e.g. "A",
  "A.1", "B.2"), or "T.1", "T.2" ... if unnumbered. Eligibility rows are always
  "E.1", "E.2" ... and document rows "D.1", "D.2" ... in the order found (their
  own numbers clash with the technical ones).
- parent: the code of the criterion this one is a sub-criterion of (e.g. "A" for
  "A.1", "A.1" for "A.1.a"), or null for a top-level criterion
- stage: ELIGIBILITY (a pass/fail eligibility condition), DOCUMENT (a document
  every bid must include; see above), TECHNICAL (marks given from the bid documents) or PRESENTATION (marks given
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
- count_bands: when the marks depend on HOW MANY qualifying items (projects or
  CVs) the bidder shows, rather than on each item (e.g. "up to 3 projects - 5
  marks, 4-6 projects - 7 marks, 7 or more projects - 10 marks"), list the bands:
  [{"min": 1, "max": 3, "marks": "5"}, {"min": 4, "max": 6, "marks": "7"},
   {"min": 7, "max": null, "marks": "10"}], and give item_marks []. Otherwise []
- proof: ELIGIBILITY rows only (see above); null for every other row
- rfp_no: ELIGIBILITY and DOCUMENT rows only: the number or letter the RFP itself
  prints for the row in its own list, exactly as printed without a trailing
  dot (e.g. "3", "B", "II.4"). For an eligibility row whose proof is listed
  elsewhere, use the number from the list that states the requirement, not the
  documents list. null if the RFP prints none, and for every other row
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
 {"code": "E.1", "parent": null, "stage": "ELIGIBILITY", "title": "...",
  "rfp_text": "...", "meaning": "...", "proof": "...", "rfp_no": "1", "max_marks": null,
  "max_items": null, "kind": null, "item_marks": [], "count_bands": [],
  "scored_by": "LLM", "rfp_page": 18, "conflict": null},
 {"code": "D.1", "parent": null, "stage": "DOCUMENT", "title": "...",
  "rfp_text": "...", "meaning": "...", "proof": null, "rfp_no": "A", "max_marks": null,
  "max_items": null, "kind": null, "item_marks": [], "count_bands": [],
  "scored_by": "LLM", "rfp_page": 17, "conflict": null},
 {"code": "A", "parent": null, "stage": "TECHNICAL", "title": "...",
  "rfp_text": "...", "meaning": "...", "max_marks": "40", "max_items": null,
  "kind": null, "item_marks": [], "scored_by": "LLM", "rfp_page": 20,
  "conflict": null},
 {"code": "A.1", "parent": "A", "stage": "TECHNICAL", "title": "...",
  "rfp_text": "...", "meaning": "...", "max_marks": "15", "max_items": 5,
  "kind": "PROJECT", "item_marks": ["3"], "count_bands": [], "scored_by": "LLM",
  "rfp_page": 20, "conflict": null}],
 "general_conditions": [{"text": "...", "rfp_page": 21}]}

PAGES
{{pages}}
