"""Settings read from .env (repo root or backend/). No secrets are logged."""
from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    aws_region: str = "ap-south-1"
    s3_bucket: str = ""
    claude_model: str = "global.anthropic.claude-sonnet-4-6"

    llm_mode: str = "bedrock"            # bedrock | replay (cache only, no AWS)
    llm_cache_dir: str = "runs/_llm_cache"
    llm_max_tokens: int = 8000

    ocr_engine: str = "textract"         # textract | tesseract (local dev)
    ocr_min_chars: int = 50              # less text than this -> OCR
    ocr_min_image_ratio: float = 0.25    # image covers this much of the page -> OCR

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rfp_eval"
    db_user: str = "rfp"
    db_password: str = ""

    file_store: str = "local"            # local | s3
    local_file_dir: str = "data/files"   # local store, and the cache for S3 files
    runs_dir: str = "runs"
    session_secret: str = ""             # optional; a random key is made at start if empty
    cookie_secure: bool = False          # True when the UI is served over HTTPS

    review_confidence: Decimal = Decimal("0.80")
    quote_match_threshold: int = 90      # 0-100, fuzzy match for OCR'd quotes
    amount_tolerance: Decimal = Decimal("0.01")

    def db_conninfo(self) -> str:
        return (f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
                f"user={self.db_user} password={self.db_password}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
