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
- Store CV facts only in `page.text` and `project.cv_facts`. Only people who can reach
  the UI can read them (see Access below).
- Never log CV content, names, phone numbers or emails.
- Retention: delete bid files and page text when the tender's retention period
  ends. Keep scores, reasons and page numbers for audit.

## Browser UI (React)
- CSP `default-src 'self'` with no inline script or style; the Vite build is
  checked to contain none. Keep it that way (coding-standards.md, Frontend).
- Every write (POST) carries the session's CSRF token in `X-CSRF-Token`; the
  session cookie is `SameSite=Strict`.
- The forensic document checks (D-058) add numpy and opencv-python-headless. They
  run on the server only and call nothing outside it; no bid page leaves it (crops are
  made only by `run.py calibrate-forensics`, into a local folder, never served).
- npm packages are code we run: keep the list short, commit
  `package-lock.json`, run `npm audit` before each release.

## Access (one sign-in account)
One account from `.env` (`APP_USERNAME` / `APP_PASSWORD`; decisions.md D-042).
Every API call except `/api/v1/session` and `/api/v1/login` needs a signed-in
session (401 otherwise). The password lives only in `.env` / the ENV_FILE
secret, never in `.env.example`, git or chat; change it by editing `.env` and
restarting. Actions are recorded against the account's own `app_user` row
(created on first sign-in, named by its username; D-053), so the audit trail
names the account. Everyone shares it, so there is no per-person audit until
named accounts exist. Keep the security group limited to
the committee's IPs until there is TLS and named accounts.
