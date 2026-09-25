# Deploy on one EC2 VM (service + PostgreSQL)

Target: one EC2 instance in ap-south-1 running the Python service and
PostgreSQL 16. S3, Textract and Bedrock are called over AWS APIs.

## Instance
- Ubuntu 24.04 LTS (or Amazon Linux 2023), t3.large to start
  (2 vCPU / 8 GB; OCR runs on Textract, not the VM). 50 GB gp3, encrypted.
- **IAM instance role** with only: S3 Get/Put/Delete on `rfp-contract-bucke/*`,
  Textract `StartDocumentTextDetection` / `GetDocumentTextDetection`, Bedrock
  `InvokeModel` / `Converse` on the configured model. With a role, leave
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` empty in `.env`.
- Security group: 443 from the office/VPN range only; 22 from admin IPs only.
  **Port 5432 is never opened** — Postgres listens on localhost.

## PostgreSQL on the same VM
```bash
sudo apt-get update && sudo apt-get install -y postgresql-16
sudo -u postgres psql -c "create user rfp with password '<strong password>';"
sudo -u postgres psql -c "create database rfp_eval owner rfp;"
# postgresql.conf: listen_addresses = 'localhost'   (the default)
```
Then in `.env`: `DB_HOST=localhost DB_PORT=5432 DB_NAME=rfp_eval DB_USER=rfp DB_PASSWORD=...`

## Service
```bash
sudo apt-get install -y python3.12-venv git
git clone https://github.com/Runjhun3/rfp-contract-evaluation.git && cd rfp-contract-evaluation
cp .env.example .env && chmod 600 .env        # fill in DB + S3 values
cd backend && python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest                                        # unit tests
python run.py migrate                         # creates all tables
```

## End-to-end test (before the UI exists)
```bash
python run.py evaluate --bid "<path>/Deloitte all docs.pdf" --bidder Deloitte \
  --tender GEM/2026/B/7401395 --department "Department of Sports, MYAS" \
  --bid-date 2026-05-07 --criteria tests/golden/nsdf/criteria.json \
  --block tests/golden/nsdf/criteria_block.md --out runs/nsdf/deloitte
python run.py compare --run runs/nsdf/deloitte --bidder Deloitte \
  --expected tests/golden/nsdf/expected_scores.json
python run.py save-run --run runs/nsdf/deloitte --project "NSDF PMU 2026" --user you@dept.gov.in
```

## Backups
- Nightly `pg_dump -Fc rfp_eval` to `s3://rfp-contract-bucke/backups/` (SSE-KMS,
  lifecycle: keep 35 days). Test a restore once a month.
- `runs/_llm_cache/` is part of the audit trail: sync it to S3 nightly too.
