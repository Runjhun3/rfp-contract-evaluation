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

## Run as services (systemd) behind nginx
```ini
# /etc/systemd/system/rfp-web.service   (copy as rfp-worker.service with ExecStart=... run.py worker)
[Service]
User=rfp
WorkingDirectory=/opt/rfp-contract-evaluation/backend
ExecStart=/opt/rfp-contract-evaluation/backend/.venv/bin/python run.py web --host 127.0.0.1 --port 8000
Restart=always
[Install]
WantedBy=multi-user.target
```
nginx terminates TLS on 443 and proxies to 127.0.0.1:8000 (`client_max_body_size 160m;`
for bid uploads). In `.env`: `FILE_STORE=s3`, `COOKIE_SECURE=true`, a long `SESSION_SECRET`.
Create users with `python run.py create-user ...`.

## End-to-end test
1. Sign in → New project (NSDF details, bid closing date 2026-05-07) → upload the RFP.
2. Worker extracts criteria → check them (A.1–B.2 "Scored per" Project/CV, marks per item) → Approve.
3. Participants: add Deloitte, EY, GT, PwC → upload each bid → Evaluate.
4. Results: compare with the committee sheet (tests/golden/nsdf/expected_scores.json); open amber
   marks, record decisions, enter presentation marks.
The CLI path (`run.py evaluate` / `compare`) still works for one bidder without the UI.

## Backups
- Nightly `pg_dump -Fc rfp_eval` to `s3://rfp-contract-bucke/backups/` (SSE-KMS,
  lifecycle: keep 35 days). Test a restore once a month.
- `runs/_llm_cache/` is part of the audit trail: sync it to S3 nightly too.
