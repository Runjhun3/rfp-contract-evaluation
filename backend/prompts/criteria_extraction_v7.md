Below is the full text of an RFP issued on GeM (or one chunk of it).
Return every technical or presentation evaluation criterion and every possible
eligibility requirement. Find criteria by MEANING, not heading. Ignore process-only
clauses, blank formats/templates, and anything explicitly marked not applicable.

ELIGIBILITY: use one ELIGIBILITY stage for every pass/fail requirement and every
mandatory bid document. A mandatory document that proves another requirement belongs
in that requirement's proof, not as a duplicate row. A mandatory document with no
matching requirement is its own eligibility row. There is no DOCUMENT stage.

For an eligibility row, set classification_unsure true only when the RFP does not make
it clear whether the clause/document should be used to qualify a bidder. Otherwise set
it false. The committee will choose whether an uncertain row is considered; do not
make this judgement from headings alone.

For every criterion return code, parent, stage (ELIGIBILITY, TECHNICAL, or
PRESENTATION), title, rfp_text copied word for word, a one-sentence meaning,
max_marks (string or null), max_items (integer or null), kind (PROJECT, CV, or null),
item_marks, count_bands, proof (eligibility only), rfp_no (eligibility only),
classification_unsure (eligibility only), scored_by, and rfp_page. Technical and
presentation codes use the RFP numbering (or T.1 etc. if unnumbered); eligibility
codes may be E.1, E.2 etc. and will be normalized. Group headings have parent null,
kind null, and their RFP total; subcriteria name their parent. General conditions
applying to several criteria go once in general_conditions.

Return exactly this JSON shape:
{"criteria":[{"code":"E.1","parent":null,"stage":"ELIGIBILITY","title":"...","rfp_text":"...","meaning":"...","proof":"...","rfp_no":"1","classification_unsure":false,"max_marks":null,"max_items":null,"kind":null,"item_marks":[],"count_bands":[],"scored_by":"LLM","rfp_page":1}],"general_conditions":[{"text":"...","rfp_page":1}]}

PAGES
{{pages}}
