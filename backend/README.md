# backend — phase 1 (command line)

Scores ONE bidder's bid against an approved criteria set and compares the
result with the committee's sheet. Every step writes JSON into the run folder
and is skipped on re-run, so an interrupted run resumes where it stopped.

```
pages_text.json → pages_ocr.json → pages_labelled.json → items.json
→ items/<item>.json (LLM) → evidence_checks.json → copy_groups.json
→ criteria/<code>.json (LLM) → scores.json → comparison.md
```

Setup, commands and costs: ../docs/local-setup.md. Design: ../docs/.

| Module | Job |
| ------ | --- |
| `app/ingest/read_pages.py` | text layer + image coverage per page |
| `app/ingest/ocr.py`, `app/aws/textract.py` | OCR (Textract, or Tesseract locally) |
| `app/ingest/label_pages.py` | LLM: page type + criterion by meaning |
| `app/ingest/build_items.py` | cut the bid into items (no LLM) |
| `app/evaluate/item_eval.py` | LLM: one call per item |
| `app/evaluate/evidence_check.py` | Python: quotes on page, values match |
| `app/evaluate/copy_check.py` | Python: copies of a project agree |
| `app/evaluate/criterion_eval.py` | LLM: best N + total per criterion |
| `app/evaluate/arithmetic_check.py` | Python: re-check every number |
| `app/evaluate/flags.py` | review flags |
| `app/llm/client.py` | the only LLM entry point; cache + replay + JSON retry |
| `app/compare.py` | compare with `tests/golden/<tender>/expected_scores.json` |
