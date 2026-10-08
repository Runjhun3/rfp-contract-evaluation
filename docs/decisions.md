# Decision log

Newest first. One entry per decision: context, decision, consequence.
Never delete an entry. Add a new one that supersedes it.

## D-066 Yes/no tests are recomputed; tests against words are the AI's judgement (2026-10-07)
The AI often lists `is_completed = true` (and, for a CV, e.g. a degree) among the tests
it applied. Python compared only numbers and dates, so each showed "Could not be
recomputed from the facts; please check it": on one sample bid's evaluation, 10 items
carried it, while the fact itself is quote-verified on its own row.
- A yes/no test is recomputed: the fact's true/false (or yes/no) against the
  threshold's. It passes, or is a problem when the AI's test contradicts its own fact.
- A test against words (a threshold with no digit) is never compared letter by letter
  ("M.Arch" vs "Post Graduate in Architecture" is a judgement of meaning): it is
  recorded as the AI's judgement (`judged:`), shown with what the document says, folded
  with the passed checks when met. A failed one still backs a rejection, as before.
- No prompt change. Results saved before this keep their old note until evaluated again.

## D-065 Only the cited pages are analysed for the document checks (2026-10-07)
The document checker analysed every scanned page of a bid (stamps, signatures, a
thumbnail) before any check could start: on a 981-page bid of 970 scans, eligibility
waited well over 15 minutes of CPU for it, although the checks only ever look at the
pages their answers cite, against D-059's rule that only the documents the criteria ask
for are checked.
- A job asks the AI first; the checker is then opened on every page its answers cite
  (an eligibility job: the pages each answer quotes; an evaluation: the items' cited
  pages), analyses only those, and runs each check's document checks before anything is
  saved, so every verdict still includes them.
- Each page is analysed once per bid file and kept (`index-v2.pkl`, grown as later jobs
  cite more pages); a job compares only its own evidence pages, so its findings never
  depend on what another job analysed. The bidder's own repeated images are still
  found from the whole file (it reads only small images).
- A stamp or signature copied from a page no check cites is no longer caught as reused;
  within the documents being evaluated it still is.

## D-064 Each labelling batch sees the pages before it (2026-10-07)
Pages are labelled in batches of 20, and the first page of a batch was labelled blind.
On two sample bids that was the only place a project boundary went wrong: a new
project's header that opened a batch was not marked as a start, so two projects became
one item (and a criterion scored by the number of items could lose marks); the second
page of a completion certificate that opened a batch was called a project header.
Making every project-header page a start was rejected: across the sample bids 81 of 83
header pages without a start were pages 2-4 of one project, so it would split them.
- Each batch is shown the last 3 pages of the batch before, with the labels they were
  given, as context only; their labels are never taken again (`page_label_v5.md`).
- About 15% more input per label call. The label prompt version is part of eligibility
  screening's label folder, so a new prompt labels a bid afresh.
Checked on the two batches: the header now starts its own item and the certificate page
is a certificate; no other item boundary in them moved.

## D-063 Every document check shown with its check; forensic findings as notes (2026-10-07)
Supersedes D-058's hiding of forensic findings and its stamp-text check. The committee
saw only identifier problems: valid identifiers, forensic findings and what could not
be checked were invisible, so "nothing found" read the same as "never checked".
- Every row is shown with its check: each identifier (valid, a problem, or for its issuer
  to confirm), each forensic finding, and a last row naming what was checked and what
  could not be and why (OCR'd before word positions were kept, scanned below 90 or 150
  dpi; `forensics/coverage.py`).
- Until calibrated (`FORENSIC_FLAGS=false`), a forensic finding is a note to look at:
  it never makes a check the committee's to decide nor adds a review reason. Switched
  on, it is a problem, as before.
- A finding's box (`region`) is kept with the check (evidence_check.region, migration
  018; in an eligibility check's verification) and outlined on the bid page when its
  row is opened.
- The stamp-text check goes: on a genuine bid all its findings were genuine seals of
  issuers, auditors and the bidder, whose words naturally appear nowhere else on the
  page. With it go the bidder's names given to the checker.

## D-062 Document checks only on a verdict's own documents, shown only with it (2026-10-07)
Supersedes the Document checks page and per-finding review of D-057 and D-058, and the
eligibility evidence of D-059. The page listed findings on documents the criteria do not
ask about: an eligibility check was checked on every page tagged for it (202 pages for a
past-experience requirement on a sample bid, the bidder's own proposal write-ups among
them, giving 25 of its findings), and the page showed findings apart from the checks
whose verdicts already included them.
- An eligibility check's documents are the pages its answer quotes its facts from (as an
  item's are its cited pages); an answer quoting nothing gets no document check.
- Problems are rows of the check's own verification, shown with it: an eligibility check
  is the committee's to decide, an item goes to review (DOCUMENT_ID / DOCUMENT_FLAG). An
  identifier's note says where to confirm it (the issuer's portal); the app looks
  nothing up. What the committee found is the reason for its decision on the check.
- The export shows each problem on its check's row ("Document check: ..."); the audit
  log keeps the committee's decisions on checks and marks.
- Gone: the Document checks page and its API, the per-finding outcomes, crops shown to
  the committee, and the document_flag tables (migrations 018 and 019, never merged).
  Forensic findings are worked out only when FORENSIC_FLAGS is on; calibration makes its
  own crops for its report.

## D-061 Word positions measured per run of words, printed and legible only (2026-10-07)
Supersedes D-060's limits for scans. At 90 dpi, calibration on a genuine bid gave 113
word-position flags on 53 pages, none real: table cells centred at other heights read
as one line, handwritten dates beside signatures, words OCR barely read, and ordinary
wobble on printouts just over the limits.
- A line is split at any gap wider than 2 word heights; each run (a cell, a column) is
  measured on its own. A figure alone in a table cell is no longer compared.
- Handwritten words (Textract's TextType, kept on each word; unknown for Tesseract and
  for OCR cached before this) and words below 0.7 OCR confidence are left out.
- Scans get looser limits than text layers: baseline 0.5, height 1.6, tilt 2.5°.
- A figure's baseline follows the slant of its run (fitted through all its words, so
  a few at one end cannot tilt it), not the flat average of its bottoms: on a slightly
  rotated scan the whole line slants, and words at either end of a long line looked
  off it.
Calibrated again on the same bid (OCR cached before handwriting was kept): 6 word-position
flags on 5 pages, from 114. Forensic flags stay hidden.

## D-060 Word positions on a scan are checked from 90 dpi (2026-10-07)
Supersedes D-058's single 150 dpi floor for scans. Bids are scans of printouts that the
bidders cannot be asked to rescan; on a sample bid every evidence scan was 63-142 dpi
(median 96), so no scanned word position was ever measured. At about 96 dpi a line of
text is 10-12 pixels tall: a figure several pixels off its line or of another height is
still measurable, while grain and re-compression are not.
- Word positions on a scan (`geometry.py`) run from `MIN_POSITION_DPI` (90).
- Pixel checks (`pixels.py`) and LOW_RESOLUTION keep `MIN_EVIDENCE_DPI` (150).
Forensic flags stay hidden until `run.py calibrate-forensics` on genuine bids shows the
false alarms at this floor are rare; the floor is raised again if they are not.

## D-059 Document checks run inside each criterion check, on its required documents (2026-10-07)
Supersedes the trigger and scope of D-057 and D-058. Calibrating on a genuine bid gave
145 flags on 88 of 416 pages, nearly all on the bidder's own designed pages and mock-ups,
and a verdict reached before the documents were checked would have to change after.
- What is checked: only the documents the criteria ask for, as the checks already find
  them. For an eligibility requirement, the pages given to its check as proof; for an
  evaluated item, the pages cited as the RFP's proof and those its facts are quoted
  from. No list of document types: the criteria decide.
- When: with the check itself. The eligibility job and the evaluation open the bid's
  document checker (`forensics/checker.py`) on pages they already read and OCR'd; it
  never OCRs and never calls the AI. Its bid-wide reference (marks, scan thumbnails,
  the bidder's own repeated images) is built once per file from those pages.
- Verdict: an identifier failing a check needing no issuer (and, once calibrated, a
  forensic finding) is part of the check's own verification. An eligibility check
  whose proof is flagged is for the committee from the start (like an unsure answer),
  and deciding it needs a reason; an item gets the review reason DOCUMENT_ID or
  DOCUMENT_FLAG. The separate CHECK_DOCUMENTS job and "Check documents again" go.
- Fixes found by calibration: only words inside a scan count (not the bidder's caption
  above it); the issuer's letterhead and margins are read within each scan; a near copy
  needs a changed date or amount that is not OCR noise (a digit changed to another digit
  always counts); a stamp naming the bidder, like its repeated images, or a notary's is
  not flagged; a paragraph is not a stamp; a missing page is a gap inside a document's
  numbered pages, not its unnumbered first page; copied patches need the text's place.
On the same two bids, from their existing evaluation runs: 14 flags on 12 of 192
evidence pages and 1 on 1 of 162, without OCR word boxes (those runs predate them).

## D-058 Forensic document checks within each bid, hidden until calibrated (2026-10-07)
On top of D-057's basic checks, four forensic checks, in their own job,
CHECK_DOCUMENTS, queued on bid upload (or "Check documents again"). Every check works
within the one bid only (bids carry different kinds of documents); every finding is a
flag with a crop of its region, never a verdict.
- Groundwork: a bid file is read and OCR'd once for every job (`runs/files/<file_id>`);
  OCR keeps each word's box and confidence (Textract and Tesseract); text layers give
  each word's font, size and letter spacing (`forensics/words.py`); scans are read as
  stored in the PDF, not re-rendered (`forensics/images.py`).
- Word positions (`geometry.py`): a figure off its line's baseline, of another height,
  overlapping a word, on a tilted line, or on a text layer in another font, a slightly
  different size or unevenly spaced. Headers, footers, page numbers and designed
  callouts are left out.
- Stamps and signatures (`marks.py`, `stamps.py`): round stamps and signatures in
  coloured ink, round seals on greyscale scans; the same mark image on two pages (a
  real stamp never prints exactly alike), and a stamp whose words are not on the rest
  of its page. Left out: the bidder's own seal and signature (like an image it repeats
  on its pages), a scan shown twice (one certificate under two criteria: on the sample
  bids 106 of 109 first flags were this), highlight frames, letterhead logos and
  coloured print.
- Layout (`layout.py`): a letter reused with other figures (near copy), printed page
  numbers that jump (missing pages), a page unlike the others under its letterhead.
- Pixels (`pixels.py`): a figure that re-compresses (JPEG) or has grain unlike its
  line, and a copied patch outside the text.
Word positions and pixels on a scan run only at 150 dpi and above; most scans in the
sample bids are below, so those checks rarely run there: they are left out, not guessed.
The committee marks each flag "Looks fine", "Needs follow-up" or "Confirmed problem"
(append-only). Flags stay hidden (`FORENSIC_FLAGS=false`) until `run.py
calibrate-forensics` on genuine bids shows false alarms are rare.
Fixed on the way: local Tesseract ran PDFium from four threads (not thread-safe) and
decoded its UTF-8 output as the Windows code page.

## D-057 Basic document checks, within each bid, as flags for the committee (2026-10-07)
Bids arrive as merged PDFs of phone photos and scans; the originals and their digital
signatures cannot be asked for. So the system cannot prove a document genuine; it can
find what is worth confirming with the issuer. Every check works within one bid,
never across bids (bids carry different kinds of documents), and only raises a flag:
- Identifiers (`evaluate/identifiers.py`): UDIN (its membership number and year must
  match the page), CA certificates without a UDIN, GSTIN (check digit), CIN, LLPIN, an
  organisation's PAN (a person's PAN is never listed), bank guarantee numbers. Read
  in the jobs that already OCR the bid; shown on the firm's "Document checks" page,
  where the committee records what the issuer said (append-only `document_flag_review`).
- In each item (`evaluate/document_checks.py`, item_eval_v5): dates out of order, a
  stated total or average that does not add up, the firm's claim differing from its
  document (both quotes verified), a referred document missing from the item, and
  evidence from a scan under 150 dpi. Eligibility checks get the total and resolution
  checks (eligibility_check_v2). They appear as review reasons on the evidence page.
Stamp, signature, word-position, pixel and layout checks follow, off until calibrated.

## D-056 The rule text follows the criteria unless the committee wrote its own (2026-10-06)
The rule text was drafted once, at extraction; "Save changes" stored criteria edits and
the rule text box apart, so the evaluator kept the old marks, limits and wording.
Now (`app/rule_text.py`), when a saved edit changes what the criteria would draft
(marks, limits, meaning, allowed marks, scored per, AI or committee), the rule text is
redrafted with `build_block`, exactly as an extraction drafts it, and saved as the
draft (a new version to approve after an approval). Edits that do not reach the rule
text (eligibility rows, leaving one out) change nothing. The committee's own text wins
(option a): if it typed in the box in the same save, or the saved text differs from
what the unchanged criteria give, it is kept and a notice says so. "Rebuild from the
criteria" fills the box from the saved criteria for review; nothing is saved until
"Save changes". The RFP's general conditions come from the latest extraction (kept
since 016); for older projects they are read back from the saved rule text, which is
safe because an update needs that text to redraft exactly.

## D-055 The audit trail is shown in the export only (2026-10-06)
Supersedes the "Change history" cards of D-053 and D-054 on the Criteria and
Participants pages: they are removed, so those pages show only the work. Everything
is still recorded as before and shown in the export's "Audit log" sheet (criteria
setup; participants, firms and jobs; approved criteria; committee marks). The results
page keeps its hover note on committee marks, and the eligibility grid its note on
who started a firm's check.

## D-054 Participants, firms, jobs and approvals join the audit trail (2026-10-01)
Follows D-053 (migration 017).
- Participants: ticking or unticking a firm records "Participant added / removed"
  with who and when (no reason asked). Only real changes are recorded.
- Firm list: "Firm added", "Firm renamed" (adding a known legal name with a new short
  name used to overwrite it silently) and "Firm deleted". Before an unused firm is
  deleted, each project it was ticked in records its removal, so the project's own
  trail keeps it. Events keep the firm's name as it was.
- Jobs: each job keeps who queued it and which action did (RFP uploaded, criteria
  approved, bid uploaded, check eligibility again, evaluation started); automatic
  checks are credited to the person whose action queued them. The eligibility grid
  shows it on a firm's status.
- Approval: the criteria as they stand are kept with the approved rule text, so each
  run (which points to its approved version) can be traced to the exact criteria.
Shown on the Participants page ("Change history") and in the export's "Audit log".

## D-053 An audit trail for the project setup and committee marks (2026-10-01)
Committee decisions on marks and eligibility were already append-only, but the setup
around them was overwritten: criteria edits, draft rule text, committee marks and
re-extractions left no trace, and every action was recorded as "Local user".
Now (migration 016):
- Who: the `.env` account stays the one sign-in (D-042), but it gets its own
  `app_user` row on first sign-in and every action records it (`auth.current_user`).
  When named accounts come, they are new rows and the trail names each person.
- Criteria edits: each changed field is a `criterion_edit` row (old and new value),
  by the committee or by a re-extraction (the AI). Leaving out an eligibility row is
  recorded like any edit; no reason is asked for now.
- Rule text: every save of a version's text is kept (`prompt_draft_save`), with who
  created and approved each version.
- Committee marks: every mark entered is kept (`manual_score_history`); changing a
  saved mark needs a reason of at least 10 characters. The results page shows who
  entered a mark and what it replaced on hover.
- Extractions: what the AI returned each time is kept as JSON, with prompt version
  and model.
Shown on the Criteria page ("Change history") and as the export's "Audit log" sheet.
Append-only is kept by the code (rule 10), as for the other decision tables.

## D-052 A presentation is always scored by the committee (2026-10-01)
criteria_extraction_v8 dropped the stage and scorer definitions, so a presentation
criterion came back as TECHNICAL, scored by the AI. v9 states them again. Storing a
row (`app/jobs/handlers.py`) also sets scored_by COMMITTEE for every PRESENTATION row,
whatever the model returned: who marks a presentation is not a judgement call.
Projects extracted with v8 keep their rows until re-extracted; the committee can set
"Scored by: Committee only" on the Criteria page meanwhile.

## D-051 A self-corrected LLM answer uses its last JSON object (2026-10-01)
The model sometimes catches its own mistake mid-answer (e.g. an amount converted with the
wrong unit) and writes a note and a corrected JSON object after the first. The parser took
everything from the first "{" to the last "}", so the whole response failed, the retry
failed the same way, and both failures were cached and replayed on every re-run. Now
`app/llm/client.py` reads each complete JSON object and uses the last one that fits the
expected model; the correction comes after what it corrects. Nothing is repaired: Python
still verifies every fact. When neither the answer nor its retry is usable, both are
dropped from the cache, so a re-run asks the model again (replay mode keeps its cache).

## D-050 Unified eligibility screening; AI clear findings apply automatically (2026-10-01)
Mandatory bid documents and eligibility conditions are both extracted as eligibility rows.
On the Criteria page, a row can be excluded before approval; excluded rows are not sent to
the LLM and do not appear in subsequent workflow stages. The extraction model marks only
classification-uncertain rows for the committee's attention. For each considered row, a
verified MET or NOT_MET finding is the effective result immediately. Only UNSURE blocks a
firm for a committee decision. The committee may append a reasoned override to any clear
finding, retaining the existing audit trail.

## D-049 A firm's last eligibility results stay shown while it is checked again (2026-09-30)
Checking again (or replacing a bid) blanked the firm's row until the new check ended, so
a firm already decided as qualified disappeared. Now its last finished checks, their
decisions and its status stay on display, marked "Checking again…", until the new checks
replace them; the firm is not offered for evaluation meanwhile, since its bid may have
changed. Once the new check is over, only checks of the latest bid file count.
A firm unticked on the participants page keeps its eligibility results on screen
too (as on the results page), marked unticked; it is not re-checked or evaluated.

## D-048 The committee can reclassify a row between eligibility and required documents (2026-09-30)
Whether a document is pass/fail is the committee's call, not only the RFP's wording
(e.g. it may treat a missing power of attorney as disqualifying). Each screened row on
the Criteria page has "Counts as": eligibility criterion or required document. Only a
screened row can move, and only between those two (`app/criteria.py` `edited_stage`);
saving creates a new rule-text version to approve, as any criteria edit does. Firm
statuses follow at once and no check is re-run: checks do not depend on the stage.

## D-047 Screened rows show the RFP's own numbers; the E.x / D.x codes stay the key (2026-09-30)
The committee reads eligibility as the RFP numbers it (1, 2, 3 …; a documents list
A, B, C …), not as E.1 / D.1. Those RFP numbers clash across lists (a documents list's
"A" and technical criterion A), so the internal code stays the unique key and
extraction v6 copies the number the RFP prints into `criterion.rfp_no` (migration 013);
every screen and the exported sheet show it, and the code when the RFP numbers
nothing. No numbering scheme is assumed.

## D-046 Required documents are screened apart from eligibility; not disqualifying (2026-09-30)
RFPs list documents every bid must include (a signed bid form, a power of attorney,
an acceptance of terms) apart from the eligibility / pre-qualification criteria, and
only the latter make a bid non-responsive. Treating the whole list as pass/fail went
further than the RFP; the committee checked most of the documents but did not
disqualify on them. Extraction v5 returns such documents as stage DOCUMENT (codes D.1,
D.2 ...) and drops anything the RFP marks not applicable (migration 012 allows the
stage). Documents are checked and decided like eligibility criteria, but only
eligibility criteria decide who is qualified; a document decided as not submitted is
flagged on the firm ("Missing: D.2"). Undecided documents still hold the export.

## D-045 Eligibility screening before evaluation; the committee decides every check (2026-09-30)
Eligibility rows were extracted but never used, so firms that fail a pass/fail
requirement were evaluated (and paid for) like the rest. RFPs state a requirement in
one annexure and list its proof in another; extraction v4 joins them (`criterion.proof`)
and copies defining conditions (e.g. "fit and proper person") in full. Labelling v4 tags
the pages that prove each requirement; one AI check per bid and requirement returns
met / not met / unsure with quotes, and Python verifies quotes, amounts, dates and tests
as for items. Every check is only a recommendation: the committee decides each one (a
reason when the AI was unsure or the committee disagrees), and only firms decided as
meeting every requirement are evaluated. A check belongs to one bid file: replacing a
bid, or checking again, needs new decisions. Checks are not part of an evaluation run,
so each row carries its own prompt version and model instead of a run_id. Not built
yet: an "approve all" shortcut and highlighting the quote on the page image.
Consequence: extraction and labelling prompts changed, so existing projects need their
criteria re-extracted and approved again, and bids are labelled afresh once.

## D-044 Exported sheet is laid out firm by firm (2026-09-30)
The Items and Decisions sheets mixed every firm together, showed the AI's item marks
rather than the final ones, and did not say which item a decision was about. The
workbook is now a Summary sheet (criteria x firms, totals, rank; marks only) followed
by one sheet per firm in rank order: each criterion with its final marks and whether
they were approved or entered, every item the firm claimed with the AI's marks, the
committee's latest decision and reason and the final marks, then the firm's full
decision log (every decision, oldest first, naming its item). Sheet names are the
firms' short names, made valid and unique for Excel.

## D-043 Deleting a project hides it; a firm is deleted only when unused (2026-09-30)
Projects created by mistake or for testing cluttered the list, and firms added with a
typo stayed in the shared firm list. Deleting a project sets `tender.deleted_at`
(migration 010): it leaves the projects list and every project, run and evidence page,
but its bids, runs, scores and committee decisions stay (rule 10: never deleted). It is
refused while a job for the project is waiting or running. A firm is removed from the
shared list only when no project, deleted ones included, holds its bid file, an
evaluation or committee marks; the empty participant rows of projects it was merely
ticked in go with it. A firm in use stays, and unticking leaves it out of one project.
Consequence: a deleted project can only be restored in the database (clear
`deleted_at`); there is no restore button yet.

## D-042 Sign-in with one account from .env; product name BidLens (2026-09-29)
Supersedes D-024 (no login). The app is going onto a VM, and "anyone who can reach
the URL can do everything" is not acceptable for confidential bids and CVs.
One account, `APP_USERNAME` / `APP_PASSWORD` in `.env` (the server's ENV_FILE
secret); `.env.example` keeps the password blank. The API refuses every call
except `/session` and `/login` with 401 until the session is signed in
(`RequireLogin`), so the protection does not depend on the UI. Credentials are
compared in constant time, a wrong password waits 1 s, sign-in starts a fresh
session with a new CSRF token, and an empty password signs nobody in. Set
`SESSION_SECRET`, or every restart signs users out. Actions are still recorded
as the built-in "Local user"; named accounts and roles come later if the
committee needs per-person audit. The UI is renamed BidLens (sign-in page,
top bar, tab titles).

## D-041 Host with Docker Compose on one EC2 VM, deployed by GitHub Actions (2026-09-29)
Four containers from `docker-compose.prod.yml`: `web` (nginx serving the React
build and proxying /api), `api`, `worker` (same Python image) and `db` (Postgres
16 + pgvector, no host port). Supersedes the systemd setup in the old
deploy-ec2.md. A push to `dev` runs the tests; if they pass, GitHub Actions copies
the commit (`git archive`) and the `ENV_FILE` secret to the VM over SSH and runs
`deploy/remote-deploy.sh`, which builds the images on the VM. Chosen over pushing
images to a registry: no registry credentials on the VM and nothing else to run;
the trade-off is a build on the VM at each deploy (a few minutes on t2.xlarge).
The site is plain http until a domain and TLS are added; with no login (D-024)
the security group must admit only the committee's IPs.

## D-040 Item overrides: a number up to the per-item maximum (2026-09-29)
Supersedes the list part of D-037. The committee types the overriding marks again;
any mark from 0 up to the most one item can earn is accepted (the highest per-item
mark the criterion lists; the criterion's max when it lists none). Under a criterion
scored by the number of qualifying items an item override is 1 (counts) or 0.

## D-039 Criteria scored by the number of qualifying items (2026-09-29)
A criterion such as "up to 3 projects - 5 marks, 4-6 - 7, 7 or more - 10" was scored
as marks per project and added up (2 each, summed, capped), which is right only by
luck. Extraction (v3) now records such bands (`criterion.count_bands`, migration
009); each item is judged qualifies (1) or not (0); Python counts the qualifying
items and applies the band, in the evaluation and in `final_score` after committee
decisions. The criterion LLM call is skipped for these criteria (nothing to choose).

## D-038 Bounded values are ranges; 0 is always an allowed item mark (2026-09-29)
A CA certificate stated turnover as "more than INR 3,000 crore"; the value could not
be parsed, so every band test was "could not recompute". A value stated as a bound
(words or symbols) is now read as a range and a test is settled only when certain
("more than 3000" is above 750; above 5000 stays open). Per-item mark lists from
value bands never include 0, which raised a false ARITHMETIC flag for a counted
item scored 0; 0 is now always allowed.

## D-037 Item overrides use the criterion's per-item marks; items grouped by final state (2026-09-29)
An override of 6 was accepted for one project of a 2-marks-per-project criterion
(only the criterion's 16 was checked), and a project overridden into the count
still showed under "Not counted" (items were grouped by the AI's outcome). An item
override must now be one of the marks one item can earn (0 or the criterion's
listed per-item marks; 0 to the criterion's max when none are listed), chosen from
a list in the form. The `final_item` view (migration 008) holds each item's final
marks and whether it counts; `final_score` totals from it and the evidence screen
groups by it, so both always agree.

## D-036 A criterion with marks is always scored and shown (2026-09-29)
On a second RFP, A.1 (average annual turnover, 5 marks) was never evaluated because
only criteria scored per project or per CV were, and results built their columns
from the scores that existed, so A.1 vanished and the maximum read 60 instead of 65.
The presentation (C, 35) was extracted as TECHNICAL, and results looked for stage
PRESENTATION, so it had no column to enter marks. Now every criterion with marks
is scored: per project/CV, once on the whole bid (kind BID: the labeller tags its
evidence pages, one item, the same checks and approval), or by the committee
(entry column per criterion, chosen by "Scored by", not stage). Results and export
take columns and maximums from the criteria.

## D-035 Every mark needs the committee's approval (2026-09-29)
A mark the AI was confident about (no review flag) used to count as settled. Now
every criterion score stays highlighted, counts as open and blocks the export until
the committee has decided every counted item (or the whole criterion, when it has
no items). Review flags still mark the ones to look at first (the dot); they no
longer decide what needs approval. Open counts use each participant's latest
evaluation only.

## D-034 The committee decides each item; accepting needs no reason (2026-09-29)
One decision per criterion hid which project the committee disagreed with and
forced a 10-character reason even to accept the AI's marks. Decisions are now per
item (`review_decision.item_id`, which the schema already had). The final marks of a
criterion are computed in the `final_score` view from the item decisions (best
max-items of the item marks, capped), so results, the project list and the export
agree. Accepting needs no reason; overriding still does. Criterion-level decisions
made before this keep their effect until an item on that criterion is decided.

## D-033 Group cap removed (2026-09-29)
Supersedes the group-cap part of D-030. The optional cap on a group heading
(`criterion.group_cap`, CAP_APPLIED, the ✎ editor, the cap columns in results and
the "capped" note in the export) is removed at the owner's request; migration 005
drops the column. A group heading's total is again the plain sum of its
sub-criteria everywhere: criteria page, results, export. The rest of D-030 (group
headings with a computed total checked against the RFP, one "Scored by" per group,
collapse/expand, the items × top mark warning) stays.

## D-032 A CV's own position decides; no zero without an explanation (2026-09-29)
GT Bharat's Project Manager CV scored 0: its team summary ran over four pages
(cover, Project Manager, Senior Consultant, Senior Consultant) and the last page's
label opened a Senior Consultant section, which overrode the CV's own correct label.
A CV now keeps the position it names; a multi-page summary opens a section only if
all its pages agree. A criterion with nothing assigned is flagged NO_ITEMS_FOUND and
says where items of its kind went. Every item result must carry a reason and, when
it earns marks, quoted evidence; a missing one joins the single re-check and is
flagged NO_PROOF if still missing.

## D-031 A rejection needs a hard fail; one CV per person (2026-09-29)
PwC's re-run still rejected two projects on a category/type doubt ("transaction
advisory, not a PMU"; "a CMO society, not a sports department") although every
numeric test passed; the prompt rule alone did not hold. The LLM now names a
hard fail for every rejection (missing document, failed test from its own
conditions, or a quoted RFP exclusion); Python checks the structure, not the
rule, and an unbacked rejection joins the same single re-check. PwC also had
one-page profiles of the same four people after their full CVs; a CV is now
matched by the labelled person's name within a criterion and scored once.

## D-030 Group headings, group cap and CAP_APPLIED (2026-09-29)
Group rows (A, B) showed as editable criteria and made the criteria page hard
to check. They are now full-width headings with no inputs of their own: a
computed total of their sub-rows (e.g. 36 = 16 + 10 + 10), checked against the
marks the RFP states for the group; one "Scored by" that is applied to every
sub-row on save ("Mixed" when sub-rows differ); and collapse/expand (expanded
on every load, not remembered). A row warns when max items × the top mark per
item differs from its marks. The scored total counts sub-rows only.
An optional group cap (`criterion.group_cap`, migration 003) is edited behind
the ✎ on the heading. When set, the group scores min(sum of sub-rows, cap).
Python applies it to the final marks when results are shown
(`app/evaluate/group_cap.py`), and keeps both numbers ("38 → 36"). A trimmed
group is marked CAP_APPLIED: information, not a review reason, so it is kept
apart from ARITHMETIC and never makes a mark need a decision.

## D-029 Python recomputes the LLM's numeric tests; one automatic re-check (2026-09-28)
PwC's run judged ₹5,89,00,000 "not above 5 crore" (A.3) and put ₹5.02 Cr and
₹5.89 Cr in the 2–5 crore band (A.2), although it had read both values
correctly. No check covered the comparison itself. The item prompt now makes
the LLM list every numeric/date test it applied, in the RFP's own thresholds;
Python recomputes each (it knows no rule, only how to compare numbers and
dates). On any difference the item goes back to the LLM once with the finding;
the second answer stands, the first is kept and the item is flagged RECHECKED.
A test still wrong after that is flagged CONDITION_MISMATCH. Python never
changes marks itself.

## D-028 Extraction: no forms, required documents, general conditions (2026-09-28)
The NSDF extraction returned three blank formats (project sheet, CV format, MII
form) as criteria, missed the Annexure II documents the committee checked, and
dropped the notes under the marks table (lead consultant in India; extra CVs
score 0). Forms are now excluded, mandatory documents become eligibility rows,
and multi-criterion notes are returned once as general conditions at the top of
the rule text. The RFP is sent in one call up to 100 pages (as this doc already
said), because a 40-page second chunk saw the forms without the table they
belong to and returned them as duplicate eligibility rows.

## D-027 The bidder's section maps items; judgement calls go to the committee (2026-09-28)
The EY run scored 43 against the committee's 65. Projects were mapped to a
criterion by their own content, so a project the bidder claimed under A.1 went
to A.2 or A.3. Now a claim summary for one criterion (mapped by meaning) owns
every item of the same kind after it; the page's own label is only a fallback.
CV tables have a text layer out of reading order (a "Total experience" line
printed under one table sits under another in the text), so CV pages are also
sent as images, the LLM lists the employment rows, and Python re-adds them.
A CV scores each sub-criterion separately; an unmet part no longer zeroes the
whole CV. The system prompt no longer names a sector: interpretation
questions (client category, "completed" for extended or phased work,
relevance, "preference" wording) are marked eligible with confidence < 0.8 for
the committee; only a missing document or a clearly failed number/date rejects.

## D-026 Group headings are not criteria (2026-09-28)
RFP marking tables nest: a heading such as "A Consultant Experience (36)" is the
sum of A.1-A.3. Counting headings and sub-criteria together doubled those marks
(an NSDF total of 165 instead of 100). A row that another row names in
`parent_code` is a group: it shows its title with editable marks, and is left out of the total, the
rule text and the evaluation run. If a group's marks differ from the sum of its
direct sub-criteria, the criteria page warns; neither number is corrected.
Groups are found from the LLM's `parent` link, never by parsing codes.

## D-025 React UI over a JSON API (2026-09-25)
Supersedes the UI part of D-022. The screens are a React single-page app
(React 19 + TypeScript + React Router, built with Vite) in `frontend/`. The
Python side is a JSON API under `/api/v1` (`{"data", "message"}` replies) in
`backend/app/web/`. Marks travel as exact strings, never JSON numbers, so the
browser never does float maths on them. In production Starlette serves the
built `frontend/dist`, so it is still one process and Node is needed only to
build, not to run. CSRF moves from a hidden form field to the `X-CSRF-Token`
header; the strict CSP stays (the build has no inline script or style).
Every screen, route and behaviour of the Jinja2 UI was carried over one-to-one.
Trade-off: a Node toolchain and npm dependencies to keep patched (`npm audit`).

## D-024 No login: one built-in local user (2026-09-25)
The login page, sign-out, roles (VIEWER/EVALUATOR/COMMITTEE/ADMIN) and
`create-user` are removed; supersedes the login/roles part of D-022. The app
opens straight to Projects and every action is recorded against one built-in
user ("Local user", migration 002_local_user), so `created_by`, `approved_by`
and `reviewer` still point at a real `app_user` row. CSRF on every form stays;
the session key is generated at start when SESSION_SECRET is empty.
Consequence: anyone who can reach the URL can do everything, and the record no
longer says which person approved or decided. Run it only on localhost or a
private network (see deploy-ec2.md). Bring back accounts (or SSO) if several
people need separate sign-offs.

## D-023 Selection method removed (2026-09-25)
The system scores only the document-based technical marks; the committee adds
presentation marks. QBS/QCBS/L1 changed nothing, so the field is gone from the
UI and the schema. 001_initial.sql was edited in place: it had not been applied
anywhere except test databases. Add a QCBS mode (with financial bids) only if needed.

## D-022 Server-rendered UI: Starlette + Jinja2, no JS build (2026-09-25)
Seven screens from the design canvas. One CSS file, one small JS file (progress
polling), strict CSP, CSRF on every form, server-side role checks, local
accounts with scrypt until SSO is chosen. Chosen over a React SPA: no node
toolchain on the VM, less code, easier security review; the trade-off is less
in-page interactivity, which these screens don't need. One bid PDF per
participant for now (Replace supported); several files per bidder later.

## D-021 "Project" means the evaluation cycle; bid sections are `bid_item` (2026-09-25)
In the UI a user creates a Project = one tender cycle (table `tender`). The
table that held one credential/CV inside a bid is renamed `bid_item` to avoid
the clash.

## D-020 Plain SQL migrations + psycopg instead of SQLAlchemy/Alembic (2026-09-25)
Supersedes the DB part of D-010. ~20 tables, queries in one folder, and a DBA
at the ministry who should be able to read exactly what runs. Plain SQL files
are simpler and were tested directly on PostgreSQL 16. Revisit if the query
code grows past what one folder holds comfortably.

## D-019 NSDF golden run uses bid date 2026-05-07 (2026-09-25)
GeM shows the original end date 14-04-2026; it was extended and bids were
opened on 07-05-2026. The final closing date should be confirmed from GeM;
07-05-2026 is used until then. Only affects the "awarded >= 12 months before"
rule (Deloitte Credential-11, awarded Feb 2026, fails either way).

## D-018 difflib instead of rapidfuzz (2026-09-25)
Standard-library fuzzy matching is enough for 200-character quotes on
one page, and removes a dependency.

## D-017 OCR any page with a large image, not only empty pages (2026-09-25)
Scanned certificates sit under a typed caption, so they have a text layer.
Rule: OCR when text < 50 chars OR images cover >= 25% of the page
(Deloitte: 253 pages instead of 54).

## D-016 Phase 1 = command-line pipeline with a JSON run folder (2026-09-25)
Get scoring right against the committee sheet before adding Postgres, the
job queue and the API. Run-folder files mirror schema.md tables, so phase 2
is a storage swap, not a redesign. Every LLM answer is cached on disk for
audit and free re-runs.

## D-015 Out of scope for now (2026-09-25)
Comparing judgements across bidders, certificate authenticity (forgery,
UDIN), stamp/signature detection. Each bid is evaluated only on its own
evidence.

## D-014 Map by meaning, not by wording (2026-09-25)
RFPs and bids word the same criterion differently. Criteria are extracted
with a plain `meaning`; pages and items are mapped to criteria by the LLM
against that meaning, with a confidence. No regex on headings or annexure
names. Keeps the system usable on RFPs other than NSDF.

## D-013 Each copy of a project is its own item; copies must agree (2026-09-25)
Supersedes the "read once" part of D-005. Bidders repeat the full document
set per criterion. Each copy is judged under its own criterion; COPY_CHECK
groups copies and flags any disagreement on client, value or dates.

## D-012 Python verifies every relied-on quote (2026-09-25)
The LLM returns page + exact quote for every fact its decision depends on.
Python checks the quote is on that page (exact, or fuzzy >= 90 for OCR) and
states the value/date used. Failure flags the item; it never auto-corrects.
The same check blunts hidden instructions in bid text: a mark can't stand
without verifiable evidence. Prompt v1 files were revised before first use,
so no v2 was needed.

## D-010 Python service (2026-09-25)
The team's AWS setup and scripts are Python. Decision: FastAPI + SQLAlchemy +
Alembic, with a Postgres-backed job queue (no Celery or Redis). One less moving
part; the job volume (~150 LLM calls per run) doesn't need a broker.

## D-009 S3 + Textract in ap-south-1; Claude Sonnet 4.6 on Bedrock (2026-09-25)
Bucket `rfp-contract-bucke`. Open: the `global.` model profile may route outside
India. See security.md. Must be closed before live bids.

## D-008 Presentation marks fully manual (2026-09-25)
35 marks, entered by the committee. It is the most subjective part and the most
likely to be challenged.

## D-007 Eligibility = "document present on page X" (2026-09-25)
No signature/stamp detection for now. Revisit if the committee asks for it.

## D-006 Max-N policy = best N, tie → bidder's order (2026-09-25)
Written into `criterion_eval_v1.md`. Not left to the LLM's choice.

## D-005 One LLM call per project, then one per criterion (2026-09-25)
GT's A.2 section alone is 261 mostly scanned pages, which is too big for one call.
Projects are read once and judged under every criterion they're claimed for.

## D-004 Anchors, not the bidder's index (2026-09-25)
Index quality varies from per-project (Deloitte) to one line for 682 pages
(GT). Claim summary pages and project header pages exist in all four NSDF
bids.

## D-003 PDF page numbers only (2026-09-25)
The committee cites PDF pages. Printed numbers are unreliable (GT p.94 = "76").

## D-002 Rules in versioned prompts; Python checks numbers (2026-09-25)
The committee can read the rules against the RFP, and there's no rules engine
to maintain. Python recomputes totals/caps; mismatch → review, never auto-fix.

## D-001 PostgreSQL + pgvector (2026-09-25)
The data is relational and small (~2,000 pages per tender). Scoring needs
exact numeric comparisons. A columnar DB suits analytics over billions of
rows, and a vector-only DB can't do the joins/audit. Rejected both.

## D-000 Inputs = RFP + bid documents only (2026-09-25)
Pre-bid queries/corrigenda are not ingested. If a corrigendum changes a rule,
the criteria block gets a new version by hand.
