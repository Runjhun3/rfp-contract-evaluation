# Decision log

Newest first. One entry per decision: context, decision, consequence.
Never delete an entry. Add a new one that supersedes it.

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
