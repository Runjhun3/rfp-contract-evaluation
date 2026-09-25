"""boto3 clients are built here and nowhere else."""
import os
from functools import lru_cache

from app.config import Settings

# boto3 reads credentials only from the process environment (or ~/.aws), not from
# .env. Local runs keep them in .env, so they are copied across before any client.
CREDENTIAL_ENV = {"AWS_ACCESS_KEY_ID": "aws_access_key_id",
                  "AWS_SECRET_ACCESS_KEY": "aws_secret_access_key",
                  "AWS_BEARER_TOKEN_BEDROCK": "aws_bearer_token_bedrock"}


def export_credentials(settings: Settings) -> None:
    """Values already in the environment win; blank ones are skipped, so on EC2
    (keys left empty) boto3 falls back to the instance's IAM role."""
    for env_name, field in CREDENTIAL_ENV.items():
        value = getattr(settings, field)
        if value:
            os.environ.setdefault(env_name, value)


@lru_cache
def _client(service: str, region: str):
    import boto3
    from botocore.config import Config

    config = Config(retries={"mode": "adaptive", "max_attempts": 5}, read_timeout=300)
    return boto3.client(service, region_name=region, config=config)


def client(service: str, settings: Settings):
    export_credentials(settings)
    return _client(service, settings.aws_region)
