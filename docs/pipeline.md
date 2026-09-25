# Pipeline

Read alongside schema.md (tables) and prompts.md (prompt files). Each step
below is one job `kind` in the `job` table, handled in `app/jobs/handlers.py`.

Two rules run through every step:
- **Map by meaning, not by wording.** RFPs and bids word the same criterion
  differently ("Annexure III" vs "Marking scheme", "Evaluation Criteria A2" vs
  "Sports consulting assignments above INR 1 crore"). Criteria and bid
  sections are matched on meaning by the LLM against the tender's own
  criterion list. No regex on headings, no hard-coded annexure names.
- **Every counted item is backed by a verified quote.** The LLM quotes the
  exact words it relied on; Python finds that quote on the cited page and
  checks it states the value or date used.

## 1. RFP → approved prompt (day 0)
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | INGEST_FILE | Store the RFP in S3 (`tenders/<id>/rfp/<sha256>.pdf`), extract text per page (Textract for scanned pages). |
| 2 | EXTRACT_CRITERIA | Send the whole RFP (≤ 100 pages; larger → 40-page chunks) with `criteria_extraction_v1.md`. The LLM finds eligibility and evaluation criteria **by meaning**, wherever they sit and whatever they are called. Writes `criterion` rows: verbatim `rfp_text`, a one-line plain `meaning`, `max_marks`, `max_items`. |
| 3 | — (API) | Render the criteria block from `criterion` rows into `evaluation_prompt` v1 (DRAFT). |
| 4 | — (API) | Human compares the block with the RFP, edits, approves → PROMPT_APPROVED. |

## 2. Bid → pages → items (days 15–20, per file)
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | INGEST_FILE | sha256 check (re-upload = no-op). Store in S3. pypdfium2 reads the text layer of every page → `page` rows. `pages_done` updated as it goes, so the job can resume. |
| 2 | OCR_PAGES | Pages with < 50 chars of text are bundled into one PDF under `tmp/<file_id>/` and sent to Textract `StartDocumentTextDetection` (async). Text + confidence go back into `page`. tmp object deleted. |
| 3 | LABEL_PAGES | Batches of ~20 pages (first 1,500 chars each) + the tender's criterion list (`code — meaning`) with `page_label_v1.md`. Sets `page_type`, and for summary/header/CV pages the `criterion_code` whose **meaning** matches, with `map_confidence`. Also checks the cover page for the GeM bid no. |
| 4 | BUILD_PROJECTS | Deterministic Python. Each `PROJECT_HEADER` page starts an item that runs until the next header, CV or section break. **Each item belongs to exactly one criterion.** If a bidder repeats the same project under A.1, A.2 and A.3, that is three items (three copies). Items are cross-checked against the `CLAIM_SUMMARY` page (count, page ranges); differences are flagged. |

For NSDF expect ~0% OCR (EY, PwC) up to ~62% (GT: 505 of 819 pages).
Start ingestion as soon as a bid is uploaded, not when the run starts.

## 3. Evaluation run
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | EVAL_ITEM (one per item) | `system_v1` + criteria block (cached) + `item_eval_v1` + only this item's pages, each prefixed `[PDF p. N]`. Returns facts, **each with page + exact quote**, `relies_on`, eligible, marks, reason, confidence, and any suspicious text. Writes item facts + draft `claim`. |
| 2 | (same job) | `evidence_check.py` — see below. Writes `evidence_check` rows. |
| 3 | COPY_CHECK (one per bidder, after all EVAL_ITEM) | `copy_check.py` groups copies of the same project (same client + similar title) and compares client, value and dates. Any difference → `COPY_MISMATCH` on every copy. |
| 4 | EVAL_CRITERION (one per bidder × criterion) | `criterion_eval_v1` + item results JSON only (no pages). Applies max N / best N → counted flags + total. Updates `claim.counted`, writes `criterion_score.llm_marks`. |
| 5 | (same job) | `arithmetic_check.py`: `checked_marks` = sum of counted claim marks, capped at `max_marks`; counted ≤ `max_items`; each item mark allowed by the prompt; duration recomputed from verified dates. Sets `arithmetic_ok`. |
| 6 | (same job) | `flags.py` sets `needs_review` + `review_reasons`. |

### Evidence check (`evaluate/evidence_check.py`)
For every item the LLM marks eligible:
1. It cites at least one work-order page and one completion/CA page.
2. For every fact in `relies_on` (e.g. `value_inr`, `end_on`), the quote is
   found on the cited page: exact match after normalising whitespace and
   case, else fuzzy match ≥ 90 (rapidfuzz `partial_ratio`) to tolerate OCR noise.
3. The quote actually states the value used: amounts are parsed to rupees
   (₹, Rs., INR, crore/Cr, lakh/lac, Indian digit grouping) and must match the
   fact within 1%; dates are parsed day-first and must match exactly.
4. Any failure → `EVIDENCE_UNVERIFIED` flag. Python does not change the LLM's
   decision; the committee sees exactly which quote failed and why.

### Review flags
| Code | Raised when |
| ---- | ----------- |
| ARITHMETIC | `llm_marks` ≠ `checked_marks`, or a cap is exceeded |
| EVIDENCE_UNVERIFIED | a counted item lacks a certificate page, or a quote is not on its page, or does not state the value/date used |
| COPY_MISMATCH | copies of the same project disagree on client, value or dates |
| MAPPING_UNSURE | an item's criterion mapping has confidence < 0.80, or disagrees with the bidder's summary page |
| LOW_CONFIDENCE | any claim confidence < 0.80 |
| OCR_EVIDENCE | a cited evidence page came from Textract/vision |
| MISSING_FACT | date, value or evidence missing for an item |
| SUMMARY_MISMATCH | LLM's value/status differs from the bidder's summary page |
| SUSPICIOUS_TEXT | a page contains text addressed to the evaluator (instructions, "award full marks") |
| NO_ANCHOR | an item was found only by search, not a header page |

## 4. Committee
1. Review screen lists every claim: counted/excluded, reason, quotes with
   pass/fail, link to the S3 page (presigned URL, 15 min).
2. Reviewers accept or override with a reason (append-only `review_decision`).
3. Committee enters presentation marks (`manual_score`).
4. Export: `export/annexure_sheet.py` writes the committee's existing
   *ANNEXURE III EVALUATION* layout: marks + PDF page ranges per bidder.

## Out of scope (for now)
- Comparing judgements across bidders: each bid is evaluated on its own evidence.
- Authenticity of certificates (forgery, UDIN checks).
- Signature / stamp detection.

## Volumes (NSDF, 4 bidders)
- ~2,050 pages, ~690 OCR'd.
- ~40–50 item calls per bidder (copies now count separately) + 5 criterion
  calls ≈ 200 Bedrock calls/run.
- Largest single item call: GT A.2 project 5, 74 pages.
