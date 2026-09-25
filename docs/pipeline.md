# Pipeline

Read alongside schema.md (tables) and prompts.md (prompt files). Each step
below is one job `kind` in the `job` table, handled in `app/jobs/handlers.py`.

## 1. RFP → approved prompt (day 0)
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | INGEST_FILE | Store the RFP in S3 (`tenders/<id>/rfp/<sha256>.pdf`) and extract its text per page. |
| 2 | EXTRACT_CRITERIA | Send the Annexure II/III pages with `criteria_extraction_v1.md`. Write `criterion` rows (verbatim `rfp_text`, `max_marks`, `max_items`). |
| 3 | — (API) | Render the criteria block from the `criterion` rows into `evaluation_prompt` v1 (DRAFT). |
| 4 | — (API) | A human compares the block with the RFP, edits it, and approves it. The tender moves to PROMPT_APPROVED. |

## 2. Bid → pages → projects (days 15–20, per file)
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | INGEST_FILE | sha256 check (re-upload = no-op). Store in S3. Use pypdfium2 to read the text layer of every page and write `page` rows. Update `pages_done` as it goes, so the job can resume. |
| 2 | OCR_PAGES | Pages with < 50 chars of text are bundled into one PDF under `tmp/<file_id>/` and sent to Textract `StartDocumentTextDetection` (async). Text and confidence go back into `page`. The tmp object is deleted. |
| 3 | LABEL_PAGES | Batches of ~20 pages (first 1,500 chars each) are sent with `page_label_v1.md`. This sets `page_type` and `criterion_hint`, and checks the cover page for the GeM bid no. |
| 4 | BUILD_PROJECTS | Deterministic Python. Each `PROJECT_HEADER` page starts a project that runs until the next header, CV or section break. `claimed_codes` comes from `criterion_hint` and the `CLAIM_SUMMARY` table. Mismatches (count, page range) are logged as flags. |

For NSDF, expect ~0% OCR (EY, PwC) up to ~62% (GT: 505 of 819 pages).
Start ingestion as soon as a bid is uploaded, not when the run starts.

## 3. Evaluation run
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | EVAL_ITEM (one per project/CV) | `system_v1` + criteria block (cached) + `item_eval_v1`, plus only this project's pages, each prefixed `[PDF p. N]`. Returns facts + per-criterion eligible/reason/marks/evidence pages/confidence. Writes the `project` facts and draft `claim` rows. |
| 2 | EVAL_CRITERION (one per bidder × criterion) | `criterion_eval_v1` + the item results JSON only (no pages). Applies max N / best N and returns counted flags and the total. Updates `claim.counted`, writes `criterion_score.llm_marks`. |
| 3 | (same job) | `arithmetic_check.py`: `checked_marks` = sum of counted claim marks, capped at `max_marks`; counted ≤ `max_items`; each item mark allowed by the prompt. Sets `arithmetic_ok`. |
| 4 | (same job) | `flags.py` sets `needs_review` + `review_reasons`. |

`EVAL_CRITERION` for a bidder waits until every `EVAL_ITEM` for that bidder is DONE.

### Review flags
| Code | Raised when |
| ---- | ----------- |
| ARITHMETIC | `llm_marks` ≠ `checked_marks`, or a cap is exceeded |
| LOW_CONFIDENCE | any counted or excluded claim has confidence < 0.80 |
| OCR_EVIDENCE | a cited evidence page came from Textract/vision |
| MISSING_FACT | date, value or evidence is missing for a claimed item |
| SUMMARY_MISMATCH | the LLM's value/status differs from the bidder's summary page |
| NO_ANCHOR | a project was found only by search, not a header page |

## 4. Committee
1. The review screen lists every claim with counted/excluded, the reason and a link
   to the S3 page (presigned URL, 15 min).
2. Reviewers accept or override with a reason (append-only `review_decision`).
3. The committee enters the presentation marks (`manual_score`).
4. Export: `export/annexure_sheet.py` writes the committee's existing
   *ANNEXURE III EVALUATION* layout: marks + PDF page ranges per bidder.

## Volumes (NSDF, 4 bidders)
- ~2,050 pages, ~690 OCR'd.
- ~30–40 item calls per bidder + 5 criterion calls ≈ 150 Bedrock calls/run.
- Largest single item call: GT A.2 project 5, 74 pages.
