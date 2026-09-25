# Prompts

Rules for writing prompts are in coding-standards.md ("Prompt rules"). This
file lists what exists and how the pieces fit together.

## Files in backend/prompts/
| File | Used by | Input | Output |
| ---- | ------- | ----- | ------ |
| `system_v1.md` | every evaluation call | — | role + general rules |
| `criteria_extraction_v1.md` | EXTRACT_CRITERIA | RFP Annexure II/III pages | criterion list JSON |
| `page_label_v1.md` | LABEL_PAGES | ~20 page snippets | page_type per page |
| `item_eval_v1.md` | EVAL_ITEM | one project's / CV's pages | facts + per-criterion judgement |
| `criterion_eval_v1.md` | EVAL_CRITERION | item results JSON | counted items + marks |

## How an item call is assembled
```
system:  system_v1.md                           ┐ identical for every item call
         + evaluation_prompt.criteria_block     ┘ in a run → cache point here
user:    item_eval_v1.md (filled: bidder, label, claimed_codes)
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
| `{{bidder}}`, `{{label}}`, `{{kind}}`, `{{claimed_codes}}` | bidder / project |
| `{{pages}}` | page rows, each prefixed `[PDF p. N]` |
| `{{item_results}}` | JSON of all EVAL_ITEM judgements for one criterion, with bidder order |
| `{{code}}`, `{{max_items}}`, `{{max_marks}}` | criterion |

## Changing a prompt
1. Copy `item_eval_v1.md` to `item_eval_v2.md` and edit the copy.
2. Change the constant in `app/llm/prompts.py`.
3. Run `pytest -m golden` and paste the score table into the PR.
4. Never delete `item_eval_v1.md`, because older runs point to it.
