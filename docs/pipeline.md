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
| 2 | EXTRACT_CRITERIA | Send the whole RFP (≤ 100 pages; larger → 40-page chunks) with `criteria_extraction_v2.md`. The LLM finds eligibility and evaluation criteria **by meaning**, wherever they sit and whatever they are called. Writes `criterion` rows: verbatim `rfp_text`, a one-line plain `meaning`, `max_marks`, `max_items`, `parent_code`. Blank forms (CV formats, declaration forms) are not criteria; each mandatory document in a "documents to be submitted" list is an eligibility row (always coded E.1, E.2 …); presentation/interview criteria get stage PRESENTATION. Notes that apply to several criteria come back once as general conditions and head the draft rule text. A re-extraction deletes criteria the RFP no longer yields, unless a run or committee mark refers to them. A row that another row names as its parent is a **group heading** (e.g. A = A.1 + A.2 + A.3): it is not scored, not added to the total and not put in the rule text (`app/criteria.py`). |
| 3 | — (API) | Render the criteria block from `criterion` rows into `evaluation_prompt` v1 (DRAFT). |
| 4 | — (API) | Human compares the block with the RFP, edits, approves → PROMPT_APPROVED. |

## 2. Bid → pages → items (days 15–20, per file)
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | INGEST_FILE | sha256 check (re-upload = no-op). Store in S3. pypdfium2 reads the text layer of every page → `page` rows. `pages_done` updated as it goes, so the job can resume. |
| 2 | OCR_PAGES | Pages with < 50 chars of text **or an image covering ≥ 25% of the page** are bundled into one PDF under `tmp/<file_id>/` and sent to Textract `StartDocumentTextDetection` (async). Text + confidence go back into `page`. tmp object deleted. |
| 3 | LABEL_PAGES | Batches of ~20 pages (first 1,500 chars each) + the tender's criterion list (`code — meaning`) with `page_label_v2.md`. Sets `page_type`; for a claim summary the ONE `criterion_code` whose **meaning** it claims for (null if it covers several); for header/CV pages the best match by meaning, with `map_confidence`; and the item's `title`. Section-title pages are `BLANK`. Also checks the cover page for the GeM bid no. |
| 4 | BUILD_PROJECTS | Deterministic Python. Each `PROJECT_HEADER` page starts an item that runs until the next header, CV or section break. **Each item belongs to exactly one criterion: the bidder's claim decides.** A claim summary for one criterion opens a section; every item of the same kind (project/CV) after it takes that criterion until the next claim summary or marketing page. Only items outside a section use their own page's label. If a bidder repeats the same project under A.1, A.2 and A.3, that is three items (three copies). Items are cross-checked against the `CLAIM_SUMMARY` page (count, page ranges); differences are flagged. |

Why the image rule: bidders put a typed caption ("Documentary Evidence 5:
Letter of Completion") above a scanned certificate. A text-length rule alone
sends only 54 of Deloitte's pages to OCR; the image rule sends 253, which is
where the work orders and completion letters are.
For NSDF expect a few pages (EY, PwC) up to most of the evidence (GT, Deloitte).
Start ingestion as soon as a bid is uploaded, not when the run starts.

## 3. Evaluation run
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | EVAL_ITEM (one per item) | `system_v2` + criteria block (cached) + `item_eval_v3` + only this item's pages, each prefixed `[PDF p. N]`. For a CV the page images are sent too (≤ 20), because CV tables often have a text layer out of reading order. Returns facts, **each with page + exact quote**, `relies_on`, eligible, marks, reason, confidence, and any suspicious text. It also lists every numeric/date test it applied (`conditions`: fact, test, threshold, met); Python recomputes each one (`condition_check.py`) and, if any result differs, sends the item back ONCE with `item_recheck_v1` stating what differs. The second answer stands; the first is kept on record (`recheck`) and shown to the committee. A CV also returns its employment rows, the experience years used and one score per sub-criterion (marks = their sum). Judgement calls (client category, completion of extended/phased work, relevance) are marked eligible with confidence < 0.8 for the committee; only hard fails are rejected. Writes item facts + draft `claim`. |
| 2 | (same job) | `evidence_check.py` — see below. Writes `evidence_check` rows. |
| 3 | COPY_CHECK (one per bidder, after all EVAL_ITEM) | `copy_check.py` groups copies of the same project (same client + similar title) and compares client, value and dates. Any difference → `COPY_MISMATCH` on every copy. |
| 4 | EVAL_CRITERION (one per bidder × criterion) | `criterion_eval_v1` + item results JSON only (no pages). Applies max N / best N → counted flags + total. Updates `claim.counted`, writes `criterion_score.llm_marks`. |
| 5 | (same job) | `arithmetic_check.py`: `checked_marks` = sum of counted claim marks, capped at `max_marks`; counted ≤ `max_items`; each item mark allowed by the prompt; a CV's marks equal the sum of its sub-scores; duration recomputed from verified dates. Sets `arithmetic_ok`. |
| 6 | (same job) | `flags.py` sets `needs_review` + `review_reasons`. |

### Evidence check (`evaluate/evidence_check.py`)
For every item the LLM marks eligible:
1. It cites at least one work-order page and one completion/CA page.
2. For every fact in `relies_on` (e.g. `value_inr`, `end_on`), the quote is
   found on the cited page: exact match after normalising whitespace and
   case, else fuzzy match ≥ 90 (difflib partial match) to tolerate OCR noise.
3. The quote actually states the value used: amounts are parsed to rupees
   (₹, Rs., INR, crore/Cr, lakh/lac, Indian digit grouping) and must match the
   fact within 1%; dates are parsed day-first and must match exactly.
4. For a CV, every employment-row quote is on its page, and `cv_check.py`
   re-adds the rows (overlaps once, "present" = bid submission date). A total
   a year or more away from the years the LLM used fails the check.
5. Every test in `conditions` is recomputed from the fact values
   (duration from the verified dates, CV years from the employment rows); a
   test that cannot be recomputed is recorded as such, never guessed.
6. Any failure → `EVIDENCE_UNVERIFIED` flag (a wrong test → `CONDITION_MISMATCH`). Python does not change the LLM's
   decision; the committee sees exactly which quote failed and why.

### Review flags
| Code | Raised when |
| ---- | ----------- |
| ARITHMETIC | `llm_marks` ≠ `checked_marks`, or a cap is exceeded |
| EVIDENCE_UNVERIFIED | a counted item lacks a certificate page, or a quote is not on its page, or does not state the value/date used |
| COPY_MISMATCH | copies of the same project disagree on client, value or dates |
| CONDITION_MISMATCH | a numeric/date test the LLM applied still gives a different result when Python recomputes it, after the one re-check |
| RECHECKED | Python recomputed a test differently, so the item was re-evaluated once; the first and second answers are both on record |
| MAPPING_UNSURE | an item's criterion mapping has confidence < 0.80, or disagrees with the bidder's summary page |
| LOW_CONFIDENCE | any claim confidence < 0.80 |
| OCR_EVIDENCE | a cited evidence page came from Textract/vision |
| MISSING_FACT | date, value or evidence missing for an item |
| SUMMARY_MISMATCH | LLM's value/status differs from the bidder's summary page |
| SUSPICIOUS_TEXT | a page contains text addressed to the evaluator (instructions, "award full marks") |
| NO_ANCHOR | an item was found only by search, not a header page |

`CAP_APPLIED` is not a review flag: it marks a group whose total was trimmed to
its group cap (D-030). It is computed from the final marks when results are
shown, with the uncapped sum beside the capped total, and needs no decision.

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
