# API and worker image (same image, different command). Build context: backend/
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY prompts ./prompts
COPY migrations ./migrations
COPY run.py .

# Run as a normal user; data/ (file cache) and runs/ (step files, LLM cache) are volumes.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data/files /app/runs \
    && chown -R app:app /app/data /app/runs
USER app

EXPOSE 8000
CMD ["python", "run.py", "web", "--host", "0.0.0.0", "--port", "8000"]
