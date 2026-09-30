# Prompts

Rules for writing prompts are in coding-standards.md ("Prompt rules"). This
file lists what exists and how the pieces fit together.

## Files in backend/prompts/
| File | Used by | Input | Output |
| ---- | ------- | ----- | ------ |
| `system_v2.md` | every evaluation call | — | role + general rules |
| `criteria_extraction_v6.md` | EXTRACT_CRITERIA | RFP pages | as v5, plus `rfp_no`: the number the RFP prints for each eligibility criterion and required document |
| `criteria_extraction_v5.md` (superseded) | EXTRACT_CRITERIA | RFP pages | as v4, plus required documents as stage DOCUMENT (D.1 …), apart from eligibility; anything marked not applicable is dropped |
| `criteria_extraction_v4.md` (superseded) | EXTRACT_CRITERIA | RFP Annexure II/III pages | criterion list JSON (v2: group headings + `parent`; v4: each eligibility row joined with its `proof` and defining conditions, every required document kept) |
| `page_label_v4.md` | LABEL_PAGES | ~20 page snippets + criteria + eligibility requirements (with proof) | page_type per page; v4: `eligibility`, the requirements each page proves |
| `eligibility_check_v1.md` | CHECK_ELIGIBILITY, one per bid × requirement | the requirement, the proof asked for, only its tagged pages (system: `system_v2`, no criteria block) | MET / NOT_MET / UNSURE, finding, facts with quotes, tests |
| `item_eval_v4.md` | EVAL_ITEM | one item's pages (one criterion) | facts with quotes + judgement |
| `item_recheck_v2.md` | EVAL_ITEM, only when Python recomputes a test differently or a rejection has no hard fail | the item prompt + previous answer + findings | the full item JSON again |
| `item_count_rule_v1.md` | EVAL_ITEM, added for a criterion scored by the number of qualifying items | code + bands | (part of the item JSON: marks 1/0) |
| `criterion_eval_v1.md` | EVAL_CRITERION | item results JSON | counted items + marks |

## How an item call is assembled
```
system:  system_v2.md                           ┐ identical for every item call
         + evaluation_prompt.criteria_block     ┘ in a run → cache point here
user:    item_eval_v4.md (+ page images for a CV) (filled: bidder, label, kind, code)
         + pages: "[PDF p. 285]\n<text>\n\n[PDF p. 286]\n<text> ..."
```
The criteria block is tender data (DB, human-approved). An NSDF example is
in `tests/golden/nsdf/criteria_block.md`.

## Placeholders
| Name | Source |
| ---- | ------ |
| `{{department}}` | tender.department |
| `{{bid_due_date}}` | tender.bid_due_at (date, IST) |
| `{{bid_due_minus_12m}}` | computed in Python, never by the LLM |
| `{{bidder}}`, `{{label}}`, `{{kind}}` | bidder / project |
| `{{criteria_list}}` | every criterion as `code — meaning`, one per line |
| `{{pages}}` | page rows, each prefixed `[PDF p. N]` |
| `{{item_results}}` | JSON of all EVAL_ITEM judgements for one criterion, with bidder order |
| `{{code}}`, `{{max_items}}`, `{{max_marks}}` | criterion |

## Changing a prompt
1. Copy `item_eval_v1.md` to `item_eval_v2.md` and edit the copy.
2. Change the constant in `app/llm/prompts.py`.
3. Run `pytest -m golden` and paste the score table into the PR.
4. Never delete `item_eval_v1.md`, because older runs point to it.
