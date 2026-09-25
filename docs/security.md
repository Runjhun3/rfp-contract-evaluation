# Security and data handling

Bids are commercially confidential, and CVs contain personal data (DPDP Act
2023). Treat every PDF, page row and LLM response as confidential.

## Secrets
- Local: `.env` only (git-ignored). `.env.example` has names, never values.
- Servers: AWS Secrets Manager, loaded at start-up. No keys baked into images.
- Prefer an IAM role (EC2/ECS task role) over access keys wherever possible.
- Never print, log, or paste a secret into a ticket, chat or doc. If one is
  exposed, rotate it immediately. Don't wait to "check if it was used".
- Least privilege for the app identity:
  - S3: `GetObject`, `PutObject` and `DeleteObject` on `rfp-contract-bucke/*` only
  - Textract: `StartDocumentTextDetection`, `GetDocumentTextDetection`
  - Bedrock: `InvokeModel` / `Converse` on the one configured model/profile

## Data location
- S3 bucket `rfp-contract-bucke` and Textract run in ap-south-1 (Mumbai).
- **Open item:** `CLAUDE_MODEL=global.anthropic.claude-sonnet-4-6` is a
  global cross-region inference profile. Bedrock may process requests in
  regions outside India. Before sending live bids, either switch to a
  profile/model whose processing stays in an approved geography, or record
  written approval for global routing in decisions.md.
- Bedrock does not use inputs to train models. Keep that confirmation on file.

## S3 bucket settings
- Block all public access. Default encryption SSE-KMS. Versioning on.
- Keys: `tenders/<tender_id>/rfp/…`, `tenders/<tender_id>/bids/<submission_id>/…`,
  `tmp/<file_id>/…` (lifecycle rule: delete after 1 day).
- Access for people only through presigned URLs (15 min) from the API.

## Personal data (CVs)
- Store CV facts only in `page.text` and `project.cv_facts`. They are read only by
  committee roles.
- Never log CV content, names, phone numbers or emails.
- Retention: delete bid files and page text when the tender's retention period
  ends. Keep scores, reasons and page numbers for audit.

## Access roles (first cut)
| Role | Can |
| ---- | --- |
| ADMIN | create tenders, manage users |
| EVALUATOR | upload RFP/bids, edit draft prompt, start runs |
| COMMITTEE | approve prompt, review/override scores, enter presentation marks, export |
| VIEWER | read scores (no page text, no CVs) |
