"""boto3 clients are built here and nowhere else."""
from functools import lru_cache

from app.config import Settings


@lru_cache
def _client(service: str, region: str):
    import boto3
    from botocore.config import Config

    config = Config(retries={"mode": "adaptive", "max_attempts": 5}, read_timeout=300)
    return boto3.client(service, region_name=region, config=config)


def client(service: str, settings: Settings):
    return _client(service, settings.aws_region)
