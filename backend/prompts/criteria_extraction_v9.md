Below is the full text of a GeM RFP (or one chunk). Extract every eligibility,
technical-evaluation, and presentation-evaluation criterion. Return valid JSON only.

Find criteria by MEANING, not headings. They may sit in an annexure, marking table,
pre-qualification section, or unheaded table. Do not infer a criterion from a bidder
form/template, process-only clause, payment term, penalty, or an item marked Not
Applicable. Return every row of every marks table, including group headings and all
sub-criteria; do not return general conditions instead of their criteria.

ELIGIBILITY: use one ELIGIBILITY stage for pass/fail qualification requirements and
mandatory bid documents. A mandatory document proving another requirement belongs in
that requirement's proof, not a duplicate row. A mandatory document with no matching
requirement is its own eligibility row. There is no DOCUMENT stage. Set
classification_unsure true only where the RFP genuinely does not establish whether a
clause/document should decide qualification; otherwise false.

For each row return verbatim rfp_text including notes, a one-sentence meaning, title
as the actual clause/table-row heading (never an annexure, clause, or source citation),
and source_reference as its source location such as "Annexure III, Clause 1, S.No. 1;
Clause 11". rfp_no is only the printed row number/letter, e.g. "1", "B", or "II.4";
never put a heading or source reference in rfp_no. rfp_page is the PDF page where the
clause begins.

TECHNICAL/PRESENTATION: preserve RFP codes and parent links. A group heading has kind
null and the total marks printed for the group; each child names its parent. For every
scored row capture max_marks, max_items, kind (PROJECT for an assignment, CV for a
proposed person, else null), and every possible TOTAL item mark. For slabs, list all
possible slab marks. For multi-part CV marks, list all possible sums. When marks depend
on how many qualifying items exist, return count_bands [{"min":1,"max":3,"marks":"5"}]
and item_marks [].

STAGE AND SCORER of every scored row (a group heading takes its children's):
- TECHNICAL with scored_by "LLM": marks given from the documents in the bid.
- PRESENTATION with scored_by "COMMITTEE": marks given for a presentation,
  interview or demonstration, even when the slides come with the bid. The
  committee enters these marks; never mark such a row TECHNICAL or LLM.
- ELIGIBILITY rows: scored_by "LLM".

ELIGIBILITY PROOF: join a requirement with documents that prove it even if the RFP
lists them elsewhere. Copy each proof verbatim. Documents that prove scored projects,
CVs, or presentations are not standalone eligibility rows. General conditions applying
to several criteria appear once in general_conditions, word for word with their page.

Return exactly:
{"criteria":[{"code":"E.1","parent":null,"stage":"ELIGIBILITY","title":"Bid Security / EMD","source_reference":"Annexure III, Clause 1, S.No. 1; Clause 11","rfp_text":"...","meaning":"...","proof":"...","rfp_no":"1","classification_unsure":false,"max_marks":null,"max_items":null,"kind":null,"item_marks":[],"count_bands":[],"scored_by":"LLM","rfp_page":35},{"code":"A.1","parent":"A","stage":"TECHNICAL","title":"...","source_reference":"...","rfp_text":"...","meaning":"...","proof":null,"rfp_no":null,"classification_unsure":false,"max_marks":"15","max_items":5,"kind":"PROJECT","item_marks":["3"],"count_bands":[],"scored_by":"LLM","rfp_page":20}],"general_conditions":[{"text":"...","rfp_page":21}]}

JSON SAFETY: Use double-quoted JSON strings. Escape every double quote, backslash,
newline, tab, and control character inside rfp_text, proof, source_reference, meaning,
title, and general_conditions. Before replying, verify every object/array is closed,
every property is separated by a comma, and the response is one complete JSON object.

PAGES
{{pages}}
