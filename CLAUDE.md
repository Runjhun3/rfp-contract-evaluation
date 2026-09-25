# RFP Bid Evaluation Service — index

Python service that scores GeM RFP bids with an LLM (Claude Sonnet 4.6 on
Amazon Bedrock), with a React UI in `frontend/`. A committee reviews and signs
every result. This file is the index. Read the file that matches your task
before changing anything.

| Read this                        | When you are...                                        |
| -------------------------------- | ------------------------------------------------------ |
| docs/design.md                   | new to the project, or asking "why is it like this?"   |
| docs/architecture.md             | adding a module, API, job or AWS integration           |
| docs/coding-standards.md         | writing ANY code, UI or prompt (non-negotiable rules)  |
| docs/schema.md                   | touching tables, migrations or queries                 |
| docs/pipeline.md                 | working on ingestion, OCR, page labels or evaluation   |
| docs/prompts.md                  | adding or changing a prompt                            |
| docs/testing.md                  | adding tests or checking accuracy against answer keys  |
| docs/security.md                 | handling secrets, bid files, CVs or AWS access         |
| docs/local-setup.md              | setting up a machine or running the service            |
| docs/deploy-ec2.md               | hosting the service + Postgres on one EC2 VM           |
| docs/decisions.md                | making a choice that future readers need to know about |

Living design doc (discussion + history):
https://claude.ai/code/artifact/faf974c3-74c4-4865-8160-4fdec63be5c0

## The six rules you must not break
1. Only two inputs: the RFP PDF and the bid PDFs. Nothing else is scored.
2. Evaluation rules live in versioned prompt files, never in Python `if`s.
3. Python checks every number the LLM returns (Decimal). A mismatch goes to
   review. It is never silently corrected.
4. `pdf_page_no` is the only page reference. Every fact cites a page AND an
   exact quote; Python verifies the quote is on that page and states the value.
5. Map by meaning, not by wording: criteria and bid sections are matched on
   what they mean, never by regex on headings or annexure names.
6. No secret in code, logs or git. `.env` is git-ignored.

## Glossary
- **Project (UI) = tender (DB)**: one GeM tender cycle (e.g. GEM/2026/B/7401395).
  The root of all data.
- **Criterion**: one scoring line from RFP Annexure III (A.1, A.2, B.1 ...).
- **Submission**: one bidder's upload for one tender.
- **Bid item** (`bid_item`): one project section or one CV inside a bid, submitted
  under one criterion. A project repeated under A.1/A.2/A.3 is three items
  (copies) linked by `copy_group`; Python checks copies agree.
- **Claim**: an item judged under its criterion in one run.
- **Evidence check**: Python's verification that a quote is on its page and
  states the value/date used.
- **Run**: one evaluation pass, pinned to one prompt version and one model.
