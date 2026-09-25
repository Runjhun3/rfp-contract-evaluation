# Local setup

## Prerequisites
- Python 3.12, Docker, AWS access to ap-south-1 (S3, Textract, Bedrock).
- Your own IAM credentials. Never reuse someone else's keys.

## Steps
```bash
cp .env.example .env            # fill in values; never commit .env
docker compose up -d db         # Postgres 16 + pgvector on localhost:5432
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py migrate           # alembic upgrade head
python run.py api               # http://localhost:8000/docs
python run.py worker            # in a second terminal
```

## Environment variables
| Name | Example | Notes |
| ---- | ------- | ----- |
| AWS_REGION | ap-south-1 | |
| S3_BUCKET | rfp-contract-bucke | |
| AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY | — | local only; servers use an IAM role |
| AWS_BEARER_TOKEN_BEDROCK | — | Bedrock API key, local only |
| CLAUDE_MODEL | global.anthropic.claude-sonnet-4-6 | see security.md (data location) |
| DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD | localhost / 5432 / rfp_eval / rfp / — | the container overrides host inside compose |
| WORKER_CONCURRENCY | 2 | jobs processed in parallel per worker |
| OCR_MIN_CHARS | 50 | below this a page goes to Textract |
| REVIEW_CONFIDENCE | 0.80 | below this a claim is flagged |

## Running the golden test
```bash
mkdir -p data/golden/nsdf       # copy the 5 NSDF PDFs here (not in git)
pytest -m golden -k nsdf
```

## Common problems
| Symptom | Fix |
| ------- | --- |
| `ThrottlingException` from Bedrock | lower WORKER_CONCURRENCY; the job retries with backoff |
| Textract job stuck IN_PROGRESS | large bundle; the worker polls every 10 s, up to 30 min |
| `vector` type missing | the DB image must be `pgvector/pgvector:pg16` |
