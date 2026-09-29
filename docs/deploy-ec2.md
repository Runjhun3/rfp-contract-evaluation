# Deploy on one EC2 VM (Docker + GitHub Actions)

Target: one EC2 instance in ap-south-1 running four containers from
`docker-compose.prod.yml`. S3, Textract and Bedrock are called over AWS APIs.
Why this shape: decisions.md D-041.

```
browser ──80──▶ web (nginx: React build, /api → api) ──▶ api (Python) ──▶ db (Postgres 16)
                                                         worker (jobs) ──┘   no public port
```

## Instance (current)
- `i-0beb51894135c3381`, Amazon Linux 2023, t2.xlarge (4 vCPU / 16 GB),
  40 GB disk, Elastic IP **13.204.151.164**, login user `ec2-user`.
- **Security group: the UI has no login (D-024).** Allow port 80 (and 443 once
  TLS is added) only from the committee's office/VPN IPs, and 22 only from admin
  IPs. Never 0.0.0.0/0. Port 5432 is never opened (Postgres has no host port).
- AWS access comes from the keys in the production `.env`. An IAM instance role
  with only S3 (the bucket), Textract and Bedrock rights is better: attach it and
  leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` empty.

## Pipeline (.github/workflows/deploy.yml)
On every push to `dev` (or "Run workflow" in the Actions tab):
1. **test**: backend unit tests; frontend type check, tests and build.
2. **deploy** (only if tests pass): `git archive` of the commit and the
   `ENV_FILE` secret are copied to the VM, unpacked into
   `/opt/rfp-contract-evaluation`, and `deploy/remote-deploy.sh` runs there. It
   installs Docker + compose on first run, builds the images, starts Postgres,
   applies migrations, starts api/worker/web, and checks `/api/v1/session`.

Repository secrets (GitHub → Settings → Secrets and variables → Actions):

| Secret | Value |
| ------ | ----- |
| `EC2_HOST` | `13.204.151.164` |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | the whole `.pem` file, including the BEGIN/END lines |
| `ENV_FILE` | the whole production `.env` (see below) |

Production `.env` (the `ENV_FILE` secret): the AWS keys, `S3_BUCKET`,
`AWS_BEARER_TOKEN_BEDROCK`, `CLAUDE_MODEL`, `DB_NAME`, `DB_USER`, a strong
`DB_PASSWORD`, a long `SESSION_SECRET`, `FILE_STORE=s3`, and `COOKIE_SECURE=false`
while the site is plain http (set `true` once TLS is added). `DB_HOST`/`DB_PORT`
are set by the compose file. Keep a copy as `.env.production` (git-ignored).
**Do not change `DB_PASSWORD` after the first deploy**: Postgres keeps the
password it was created with in its volume.

## Operating it (on the VM)
```bash
cd /opt/rfp-contract-evaluation
sudo docker compose -f docker-compose.prod.yml ps               # status
sudo docker compose -f docker-compose.prod.yml logs -f worker   # follow a service
sudo docker compose -f docker-compose.prod.yml restart api      # restart one service
```
Data lives in Docker volumes: `rfp_pgdata` (database), `rfp_files` (S3 cache),
`rfp_runs` (step files + LLM answer cache). Redeploys keep them; only
`docker compose down -v` deletes them.

## Try the stack locally
```bash
HTTP_PORT=8088 docker compose -p rfptest -f docker-compose.prod.yml up -d --build
docker compose -p rfptest -f docker-compose.prod.yml run --rm api python run.py migrate
# http://localhost:8088 ; remove with: docker compose -p rfptest -f docker-compose.prod.yml down -v
```

## End-to-end test
1. Open the UI → New project (NSDF details, bid closing date 2026-05-07) → upload the RFP.
2. Worker extracts criteria → check them → Approve.
3. Participants: add Deloitte, EY, GT, PwC → upload each bid → Evaluate.
4. Results: compare with the committee sheet (tests/golden/nsdf/expected_scores.json); open highlighted
   marks, record decisions, enter presentation marks.
The CLI path (`run.py evaluate` / `compare`) still works for one bidder without the UI.

## Not done yet
- **TLS**: add a domain, then a certificate (e.g. Caddy or certbot in front of
  `web`) and set `COOKIE_SECURE=true`.
- **Backups**: nightly `pg_dump -Fc` from the `db` container to
  `s3://<bucket>/backups/` (SSE-KMS, keep 35 days; test a restore monthly), and
  sync the `rfp_runs` volume's `_llm_cache/` (part of the audit trail).
