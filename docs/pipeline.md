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
| 2 | EXTRACT_CRITERIA | Send the whole RFP (≤ 100 pages; larger → 40-page chunks) with `criteria_extraction_v6.md`. The LLM finds eligibility and evaluation criteria **by meaning**, wherever they sit and whatever they are called. Writes `criterion` rows: verbatim `rfp_text`, a one-line plain `meaning`, `max_marks`, `max_items`, `parent_code`. Blank forms (CV formats, declaration forms) are not criteria; documents every bid must include but that the RFP does not state as eligibility are DOCUMENT rows (D.1, D.2 …, v5; anything marked not applicable is dropped); every eligibility requirement is one row (always coded E.1, E.2 …) that joins the requirement with the `proof` documents the RFP lists for it elsewhere and with the conditions that define it (v4); every mandatory document in a "documents to be submitted" list ends up in some eligibility row; presentation/interview criteria get stage PRESENTATION. Notes that apply to several criteria come back once as general conditions and head the draft rule text. A re-extraction deletes criteria the RFP no longer yields, unless a run or committee mark refers to them. A row that another row names as its parent is a **group heading** (e.g. A = A.1 + A.2 + A.3): it is not scored, not added to the total and not put in the rule text (`app/criteria.py`). |
| 3 | — (API) | Render the criteria block from `criterion` rows into `evaluation_prompt` v1 (DRAFT). |
| 4 | — (API) | Human compares the block with the RFP, edits, approves → PROMPT_APPROVED. |

## 2. Bid → pages → items (days 15–20, per file)
| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | INGEST_FILE | sha256 check (re-upload = no-op). Store in S3. pypdfium2 reads the text layer of every page → `page` rows. `pages_done` updated as it goes, so the job can resume. |
| 2 | OCR_PAGES | Pages with < 50 chars of text **or an image covering ≥ 25% of the page** are bundled into one PDF under `tmp/<file_id>/` and sent to Textract `StartDocumentTextDetection` (async). Text + confidence go back into `page`. tmp object deleted. |
| 3 | LABEL_PAGES | Batches of ~20 pages (first 1,500 chars each), each with the last 3 pages of the batch before and the labels they were given as context only (`page_label_v5.md`, D-064), + the tender's criterion list (`code — meaning`, whole-bid criteria marked `[whole bid]`) and the eligibility requirements (`code — meaning — proof`) with the label prompt. Any page that is evidence for a whole-bid criterion is tagged with it; every page also lists the eligibility requirements it proves (`eligibility`, several allowed, alongside its criterion). Evaluation and eligibility screening label with the same lists, so the calls are answered once (LLM reply cache). Sets `page_type`; for a claim summary the ONE `criterion_code` whose **meaning** it claims for (null if it covers several); for header/CV pages the best match by meaning, with `map_confidence`; and the item's `title`. Section-title pages are `BLANK`. Also checks the cover page for the GeM bid no. |
| 4 | BUILD_PROJECTS | Deterministic Python. Each `PROJECT_HEADER` page starts an item that runs until the next header, CV or section break. **Each item belongs to exactly one criterion: the bidder's claim decides.** A CV names the position it is proposed for, so a CV page's own label decides its criterion. A claim summary for one criterion opens a section; every project after it takes that criterion until the next claim summary or marketing page. A summary spread over consecutive pages opens a section only if all its pages point to the same criterion. Items outside a section use their own page's label. The same person's CV twice under one criterion (e.g. full CV + one-page profile) is scored once: the longest copy; the others are marked `duplicate_of` and not scored. If a bidder repeats the same project under A.1, A.2 and A.3, that is three items (three copies). Items are cross-checked against the `CLAIM_SUMMARY` page (count, page ranges); differences are flagged. |

Why the image rule: bidders put a typed caption ("Documentary Evidence 5:
Letter of Completion") above a scanned certificate. A text-length rule alone
sends only 54 of Deloitte's pages to OCR; the image rule sends 253, which is
where the work orders and completion letters are.
For NSDF expect a few pages (EY, PwC) up to most of the evidence (GT, Deloitte).
Start ingestion as soon as a bid is uploaded, not when the run starts.

## 2b. Eligibility screening (`CHECK_ELIGIBILITY`, per bid file)
Queued when a bid is uploaded after the criteria are approved, for every bid when they
are approved, and by "Check eligibility again". Reads, OCRs and labels the bid as
above (`ingest/prepare.py`), then one `eligibility_check_v1` call per requirement over
only the pages tagged as its proof (none tagged: no call, result UNSURE). Python
verifies every quote is on its page, every `*_inr` amount and `*_on` date against its
quote, and recomputes every test (`evaluate/eligibility_check.py`); nothing is
corrected and there is no automatic re-check, because the committee decides every
check (`app/eligibility.py`): a reason is needed when the AI was unsure or the
committee disagrees with it. Required documents are checked and decided the same way but
never disqualify: one decided as not submitted is flagged. Only firms decided as
meeting every eligibility criterion are evaluated; the others show on Results as not evaluated, with the reason (D-045).

## 2c. Document checks (inside each criterion check; D-057 to D-062)
No job and no page of their own: each eligibility check and each evaluated item checks
the documents its verdict rests on, as part of that verdict, so it never changes after.
The bid's document checker (`forensics/checker.py`) works on pages already read and
OCR'd (shared per-file cache `runs/files/<file_id>`): no OCR, no AI, within the bid.
1. Evidence pages: the pages an eligibility answer quotes its facts from (not every
   page tagged for the requirement); an item's cited proof pages and the pages its facts
   are quoted from. The checker is opened after the AI answers, on the union of the
   job's evidence pages, and analyses only those (D-065).
2. Identifiers on them (`evaluate/identifiers.py`), with the checks needing no issuer:
   each shown as valid, a problem, or for its issuer to confirm.
3. Forensic checks on them (`forensics/`), compared with the rest of the bid. Until
   calibrated (`FORENSIC_FLAGS`, `run.py calibrate-forensics`) each finding is a note to
   look at, with its box outlined on the page, that does not change the verdict (D-063).
   A stamp's words are not judged. On a
   scan, word positions run from `MIN_POSITION_DPI` (90) and pixels from
   `MIN_EVIDENCE_DPI` (150) (D-060); positions are measured per run of words, leaving
   out handwriting and words OCR is unsure of (D-061).
4. Problems join the check's verification and are shown only with it (D-062): an
   eligibility check becomes the committee's to decide; an item gets DOCUMENT_ID /
   DOCUMENT_FLAG. The committee's reason for its decision on the check records what it
   found; the export shows each problem on its check's row. An identifier's note says
   where to confirm it. A last row says what was checked and what could not be, and why
   (`forensics/coverage.py`).

## 3. Evaluation run
Which criteria are scored (`app/criteria.py` `scoring`): every criterion with marks,
except group headings and pass/fail eligibility rows. Per project or per CV when it
says so; once on the whole bid (kind BID, e.g. turnover) when the AI scores it but
neither applies, from one item made of all its tagged evidence pages; by the
committee (marks entered on the Results page) when "Scored by" is the committee,
whatever its stage. Results and the export take their columns and maximums from
the criteria, so a criterion never silently drops out; one not scored for a
finished participant blocks the export until that participant is evaluated again.

A criterion that gives marks by HOW MANY qualifying items the bidder shows ("up to 3
projects - 5 marks, 4-6 - 7, 7 or more - 10") carries `count_bands` (extraction v3).
Each of its items is judged qualifies (1) or not (0) (`item_count_rule_v1.md` is added
to the item call); no criterion LLM call: every qualifying item counts (up to max
items) and the marks are the band of that count (`count_bands.py`, and the
`final_score` view once the committee decides). An override is 1 or 0.

| Step | Job | What happens |
| ---- | --- | ------------ |
| 1 | EVAL_ITEM (one per item) | `system_v2` + criteria block (cached) + `item_eval_v4` (with the criterion's own RFP text) + only this item's pages, each prefixed `[PDF p. N]`. For a CV the page images are sent too (≤ 20), because CV tables often have a text layer out of reading order. Returns facts, **each with page + exact quote**, `relies_on`, eligible, marks, reason, confidence, and any suspicious text. It also lists every numeric/date test it applied (`conditions`: fact, test, threshold, met); Python recomputes each one (`condition_check.py`). A rejection must name its hard fail (`hard_fail`: a missing required document, a failed test from `conditions`, or a quoted RFP exclusion); Python checks it (`rejection_check.py`). If a test differs or a rejection has no hard fail, the item goes back ONCE with `item_recheck_v2` stating what was found. The second answer stands; the first is kept on record (`recheck`) and shown to the committee. A CV also returns its employment rows, the experience years used and one score per sub-criterion (marks = their sum). Judgement calls (client category, completion of extended/phased work, relevance) are marked eligible with confidence < 0.8 for the committee; only hard fails are rejected. Writes item facts + draft `claim`. |
| 2 | (same job) | `evidence_check.py` — see below. Writes `evidence_check` rows. |
| 3 | COPY_CHECK (one per bidder, after all EVAL_ITEM) | `copy_check.py` groups copies of the same project (same client + similar title) and compares client, value and dates. Any difference → `COPY_MISMATCH` on every copy. |
| 4 | EVAL_CRITERION (one per bidder × criterion) | `criterion_eval_v1` + item results JSON only (no pages). Applies max N / best N → counted flags + total. Updates `claim.counted`, writes `criterion_score.llm_marks`. |
| 5 | (same job) | `arithmetic_check.py`: `checked_marks` = sum of counted claim marks, capped at `max_marks`; counted ≤ `max_items`; each item mark allowed by the prompt (0 is always allowed); a CV's marks equal the sum of its sub-scores; duration recomputed from verified dates. Sets `arithmetic_ok`. |
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
   (duration from the verified dates, CV years from the employment rows; a yes/no
   test such as `is_completed = true` from the fact's true/false); a test against
   words (e.g. a degree) is the AI's judgement of meaning, shown as such (D-066); a
   test that cannot be recomputed is recorded as such, never guessed. A value a
   document states only as a bound ("more than INR 3,000 crore") is read as a
   range (`bounds.py`): a test is settled only when the whole range is on one side
   of the threshold; its number is still checked against the quote.
6. Any failure → `EVIDENCE_UNVERIFIED` flag (a wrong test → `CONDITION_MISMATCH`). Python does not change the LLM's
   decision; the committee sees exactly which quote failed and why.

### Review flags
| Code | Raised when |
| ---- | ----------- |
| ARITHMETIC | `llm_marks` ≠ `checked_marks`, or a cap is exceeded |
| EVIDENCE_UNVERIFIED | a counted item lacks a certificate page, or a quote is not on its page, or does not state the value/date used |
| COPY_MISMATCH | copies of the same project disagree on client, value or dates |
| CONDITION_MISMATCH | a numeric/date test the LLM applied still gives a different result when Python recomputes it, after the one re-check |
| RECHECKED | Python recomputed a test differently, or found a rejection without a hard fail, so the item was re-evaluated once; the first and second answers are both on record |
| NO_ITEMS_FOUND | nothing in the bid was assigned to this criterion; the summary lists the items of that kind found elsewhere (e.g. a CV assigned to another position) |
| NO_PROOF | an item result still has no reason, or earns marks without any quoted evidence, after the one re-check |
| UNSUPPORTED_REJECTION | an item is still not eligible after the re-check without a hard fail (missing required document, failed test, or quoted RFP exclusion) |
| DUPLICATE_CV | the same person's CV was found twice under this criterion; only the longest copy was scored |
| MAPPING_UNSURE | an item's criterion mapping has confidence < 0.80, or disagrees with the bidder's summary page |
| LOW_CONFIDENCE | any claim confidence < 0.80 |
| OCR_EVIDENCE | a cited evidence page came from Textract/vision |
| MISSING_FACT | date, value or evidence missing for an item |
| SUMMARY_MISMATCH | LLM's value/status differs from the bidder's summary page |
| SUSPICIOUS_TEXT | a page contains text addressed to the evaluator (instructions, "award full marks") |
| NO_ANCHOR | an item was found only by search, not a header page |
| DATE_ORDER | an item's dates are out of order: it starts after it ends, is awarded after it ends, or its certificate is dated before the work started, after the bid due date, or (completed) before the work ended |
| STATED_SUM | a total or average a document states does not equal the figures it is made of |
| CLAIM_DIFFERS | the firm's own page and a document state different values; both quotes are on their pages |
| REFERENCE_MISSING | a document refers to another (e.g. an extension letter) that is not among the item's pages |
| LOW_RESOLUTION | a page the evidence was read from is a scan below `MIN_EVIDENCE_DPI` (150); context only |

## 4. Committee
Results are per project, not per run (`app/results.py`, `/projects/<id>/results`): each
participant that is ticked or has been evaluated shows its LATEST evaluation, whichever run
it came from. A participant being evaluated (again) shows no marks or rank until that
evaluation is DONE, then its new marks; failed and never-evaluated participants stay
unranked. The page refreshes every 10 s while anyone is being evaluated. Export waits for
every participant to have a finished evaluation.

1. Evidence screen (`app/evidence_view.py`, wording in `app/evidence_labels.py`): items one line each
   (an attention dot on items that need the committee), grouped Counted / Not counted / Not scored; for the
   chosen item a verdict, a "for the committee to decide" box on judgement calls, failed
   checks first and passed checks folded. Presentation only; no score or flag changes.
   It lists every claim: counted/excluded, reason, quotes with
   pass/fail, link to the S3 page (presigned URL, 15 min).
2. Reviewers decide each item (project or CV) of a criterion (append-only
   `review_decision`, `item_id` set): accept keeps the AI's marks for the item (its
   marks if counted, else 0) and needs no reason; override sets the item's marks (any mark from 0
   up to the most one item can earn: the highest listed per-item mark, 1 for a
   count-based criterion, else the criterion's max) and
   needs a reason of at least 10 characters. The criterion's final marks
   (`final_score` view, migration 006) are the best max-items of the items' final
   marks, capped at max marks; overriding a not-counted item brings it into the count. The `final_item` view
   (migration 008) gives each item's final marks and whether it counts; the evidence
   screen groups items by it, so an item overridden into the count shows as counted.
   Every criterion needs the committee's approval, flagged or not: it is approved when
   every counted item is decided, and until then it stays highlighted on the results and
   evidence pages (flagged ones also carry a dot), counts as open, and blocks the export. A criterion with no
   items takes one decision on the whole criterion.
3. Committee enters the marks of every committee-scored criterion, e.g. a presentation
   (`manual_score`, one column each on the Results page).
4. Export (`app/export/`, `GET /projects/<id>/export.xlsx`): an Excel workbook in the
   committee's *ANNEXURE III EVALUATION* layout. Sheet *Evaluation*: one row per criterion
   in RFP order (group headings with the sum of their sub-criteria, the presentation), one column per
   participant in rank order, each cell the final marks + pages of the items counted, then
   document total, total and rank. Sheets *Items* (every item claimed, counted or not,
   with its reason) and *Decisions* (every committee decision, reason, who, when IST).
   Refused until every participant has a finished evaluation, every flagged mark is
   decided and presentation marks are saved; the API gives the reasons
   (`export_blockers`) and the Results page shows them.

## Out of scope (for now)
- Comparing judgements across bidders: each bid is evaluated on its own evidence.
- Authenticity of certificates (forgery, UDIN checks).
- Signature / stamp detection.

## Volumes (NSDF, 4 bidders)
- ~2,050 pages, ~690 OCR'd.
- ~40–50 item calls per bidder (copies now count separately) + 5 criterion
  calls ≈ 200 Bedrock calls/run.
- Largest single item call: GT A.2 project 5, 74 pages.
