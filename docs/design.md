# Design — why the system looks like this

Read alongside architecture.md and pipeline.md. The living version of this
design, with its discussion history, is at
https://claude.ai/code/artifact/faf974c3-74c4-4865-8160-4fdec63be5c0

## Problem
A ministry floats an RFP on GeM and bidders upload proposals of 350–820
pages. A committee scores each bid out of 100:

| Stage                                 | Marks     | Scored by                                   |
| ------------------------------------- | --------- | ------------------------------------------- |
| Eligibility (Annexure III, clause 1)  | Pass/fail | LLM finds each document + page; human confirms |
| A. Consultant experience (A.1–A.3)    | 36        | LLM (rules in prompt); committee confirms   |
| B. Quality of team (B.1–B.2, CVs)     | 29        | LLM (rules in prompt); committee confirms   |
| C. Technical presentation + interview | 35        | Committee only, entered manually            |

The highest total wins (QBS). This service automates the first three rows.

## What real bids look like (NSDF tender, 4 bidders)

| Bid      | Pages | Scanned pages | Index quality                  |
| -------- | ----- | ------------- | ------------------------------ |
| Deloitte | 464   | 55            | Every project listed with page |
| EY       | 416   | 2             | One entry per criterion        |
| GT       | 819   | 505           | One entry for 682 pages        |
| PwC      | 358   | 3             | One entry per criterion        |

What follows from this:
- **Don't rely on the bidder's index.** The reliable anchors are the claim
  summary page per criterion and the header page per project.
- **OCR is required.** Work orders and certificates are often scans.
- **Use PDF page numbers only.** The committee cites PDF pages. Printed
  numbers are wrong in places (GT PDF p.94 is printed "76").
- **Bidders pad their bids.** Deloitte claimed 11 projects for A.1, where
  the max is 8, and 6 passed. Every item needs a counted/excluded reason.
- **Bidders repeat projects across criteria** with a fresh copy of the
  documents each time (Deloitte's SAG Gujarat appears under A.1, A.2 and
  A.3). Each copy is its own item for its criterion; Python checks the
  copies agree on client, value and dates.
- **Wording differs everywhere.** RFPs and bids name the same thing
  differently, so criteria and bid sections are matched by meaning, never
  by exact text.
- **Quotes must be checked.** The LLM can misread a scanned value or quote
  the wrong page. Every fact it relies on carries a page and an exact quote
  that Python verifies.

## Core approach
1. The RFP is uploaded. The LLM extracts the criteria, a human approves them,
   and they become an evaluation prompt (versioned).
2. Bids are uploaded under the tender. Pages are OCR'd and labelled, and
   projects are cut out.
3. **Item call:** one LLM call per item (a project section or CV, one
   criterion) decides eligibility, with a reason and a page + exact quote
   for every fact it relies on.
   **Checks in Python:** the quote is on the page and states the value/date;
   copies of the same project agree.
4. **Criterion call:** one small LLM call per criterion applies "max N,
   keep best" and returns marks.
5. Python re-checks the arithmetic. The committee accepts or overrides, with a
   mandatory reason.

Rules live in the prompt so the committee can read them clause by clause
against the RFP. The trade-off is that LLMs can slip on caps and slabs.
Python therefore re-checks every number, and runs are pinned to temperature 0,
a prompt version and a model.

## Decisions taken
| Topic         | Decision                                                      |
| ------------- | ------------------------------------------------------------- |
| Inputs        | Only the RFP + bid documents. No pre-bid queries.             |
| Rules         | In versioned prompt files. No rules engine.                   |
| LLM           | Claude Sonnet 4.6 on Amazon Bedrock                           |
| Files / OCR   | S3 bucket `rfp-contract-bucke` + Textract, ap-south-1         |
| Database      | PostgreSQL 16 + pgvector (not a columnar or vector-only DB)   |
| Max N policy  | Best N by marks. On a tie, the one the bidder listed first.   |
| Eligibility   | "Document present on page X" only; no stamp/signature check   |
| Presentation  | Fully manual (35 marks)                                       |
| Evidence      | Python verifies every relied-on quote on its page             |
| Copies        | Each copy = own item; copies must agree, else flagged         |
| Mapping       | By meaning (LLM vs `criterion.meaning`), never by exact text  |
| Out of scope  | Cross-bidder comparison, forgery/UDIN checks, stamp detection |
| Service       | Python (FastAPI), Postgres-backed job queue                   |

See decisions.md for the reasoning behind each.

## Open points
- The model ID `global.anthropic.claude-sonnet-4-6` uses global cross-region
  inference, so it may process data outside India. Before live bids are
  sent, switch to a geography-limited profile or get written approval.
- NSDF answer key: the committee gave GT 9.5 on A.2 without saying which
  project was rejected. Ask them.

## Risks
| Risk                     | Mitigation                                                   |
| ------------------------ | ------------------------------------------------------------ |
| OCR misreads value/date  | Textract + Claude vision fallback; flag OCR'd evidence       |
| Unit confusion (Cr/lakh) | Prompt converts to rupees; Python compares with summary page |
| LLM arithmetic slip      | Python re-check; mismatch → review                           |
| Rule ambiguity           | Committee decides once, writes it into the prompt            |
| Run-to-run variation     | Temperature 0; prompt version + model stored per run         |
| Legal challenge          | Output is a recommendation; committee signs; page trail      |
| Confidential data / DPDP | See security.md                                              |
