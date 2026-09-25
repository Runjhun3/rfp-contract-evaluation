"""Where uploaded PDFs live. FILE_STORE=s3 (production) or local (development).

Keys look like tenders/<tender_id>/rfp/<sha256>.pdf. The worker needs a local
path to read a PDF, so S3 objects are cached on disk on first use.
"""
from pathlib import Path

from app.config import Settings


def put(settings: Settings, key: str, data: bytes) -> None:
    if settings.file_store == "s3":
        from app.aws.clients import client
        client("s3", settings).put_object(Bucket=settings.s3_bucket, Key=key, Body=data,
                                          ServerSideEncryption="aws:kms")
        return
    path = _local(settings, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def local_path(settings: Settings, key: str) -> Path:
    path = _local(settings, key)
    if not path.exists() and settings.file_store == "s3":
        from app.aws.clients import client
        path.parent.mkdir(parents=True, exist_ok=True)
        client("s3", settings).download_file(settings.s3_bucket, key, str(path))
    return path


def _local(settings: Settings, key: str) -> Path:
    root = Path(settings.local_file_dir).resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise ValueError(f"bad file key {key!r}")
    return path
