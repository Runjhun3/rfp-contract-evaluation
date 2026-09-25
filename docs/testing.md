# Testing

## Three levels
| Level | Command | Calls AWS? | When |
| ----- | ------- | ---------- | ---- |
| Unit | `pytest` | No, uses recorded responses in `tests/fixtures/` | every commit, CI |
| Integration | `pytest -m integration` | Local Postgres only | every PR |
| Golden | `pytest -m golden` | Yes: S3, Textract, Bedrock | any prompt or `evaluate/` change |

Must-have unit tests:
- `arithmetic_check`: slab edges (2.00 Cr → 1, 2.04 Cr → 1.5, 5.00 Cr → 1.5,
  5.01 Cr → 2), cap exceeded, best-N with a tie, Decimal rounding.
- `build_projects`: header-to-header boundaries, CV sections, a missing header.
- `prompts.py`: a missing placeholder raises an error. Loading an unknown version raises an error.
- LLM JSON parsing: invalid JSON → one retry → fail.
- `parse_amount`: "INR 9.06 Crore", "Rs. 9,06,00,000/-", "₹ 906 lakh",
  "Rs 90.6 million" (→ flag, not parsed), "9.06 Cr (inclusive of GST)".
- `parse_date`: "31.03.2023", "31/03/2023", "31st March 2023", "March 2023"
  (month-only → flag), never month-first.
- `evidence_check`: quote on page (exact), quote with OCR noise (fuzzy ≥ 90),
  quote on a different page (fail), quote present but value differs (fail),
  counted item with no completion/CA page (fail).
- `copy_check`: same project under A.2 and A.3 with equal facts (pass) and
  with different values (COPY_MISMATCH on both).
- Mapping: a header worded differently from the RFP still maps to the right
  criterion (recorded LLM fixture), and low confidence raises MAPPING_UNSURE.

## Golden test: NSDF (GEM/2026/B/7401395)
Files are NOT in git (confidential). Put them in `data/golden/nsdf/`:
RFP_Document_NSDF.pdf, Deloitte/EY/GT/PwC "all docs" PDFs.
Expected results: `tests/golden/nsdf/expected_scores.json`, from the
committee's Annexure III evaluation sheet (14.05.2026).

| Bidder | A.1 | A.2 | A.3 | B.1 | B.2 | Total / 65 |
| ------ | --- | --- | --- | --- | --- | ---------- |
| EY | 16 | 10 | 10 | 8 | 21 | 65 |
| GT Bharat | 16 | 9.5 | 10 | 8 | 21 | 64.5 |
| PwC | 16 | 9.5 | 10 | 8 | 21 | 64.5 |
| Deloitte | 12 | 9 | 10 | 8 | 21 | 60 |

Pass criteria:
1. 19 of 20 criterion cells match exactly.
2. GT A.2 is flagged (`needs_review`), not silently scored. The committee
   has not recorded which project it rejected.
3. Deloitte A.1 excludes exactly these five, with the right reason:
   Credential-7, -8 (6 months), -9 (4 months), -10 (outside India),
   -11 (awarded Feb 2026).
4. Every counted claim cites at least one work order page and one
   completion/CA page, and every relied-on quote passes the evidence check
   (or is flagged EVIDENCE_UNVERIFIED with a visible reason).
5. Deloitte's SAG Gujarat copies (A.1, A.2, A.3) are grouped in one
   `copy_group` and agree, or are flagged COPY_MISMATCH.

Known errors in the answer key (don't "fix" the system to match them):
- GT B.2 cites p.684 (a blank page); the CVs are at pp.755–781.
- PwC A.3 cites p.189 (engagement-letter terms).

Record each golden run in the PR as: prompt versions, model, cells matched,
flags raised, and cost/time.
