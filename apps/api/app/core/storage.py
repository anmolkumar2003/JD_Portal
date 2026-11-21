"""S3-compatible object storage (MinIO in development)."""

from functools import lru_cache
from typing import Any

import boto3
from anyio import to_thread
from botocore.config import Config

from app.core.config import get_settings


def _client(endpoint_url: str) -> Any:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@lru_cache
def _internal_client() -> Any:
    return _client(get_settings().s3_endpoint_url)


@lru_cache
def _public_client() -> Any:
    # Presigned URLs are signed for the host the browser will call, not the in-cluster one.
    settings = get_settings()
    return _client(settings.s3_public_endpoint_url or settings.s3_endpoint_url)


def put_object_sync(key: str, data: bytes, content_type: str) -> None:
    _internal_client().put_object(
        Bucket=get_settings().s3_bucket, Key=key, Body=data, ContentType=content_type
    )


def get_object_sync(key: str) -> bytes:
    response = _internal_client().get_object(Bucket=get_settings().s3_bucket, Key=key)
    body: bytes = response["Body"].read()
    return body


def delete_object_sync(key: str) -> None:
    _internal_client().delete_object(Bucket=get_settings().s3_bucket, Key=key)


async def put_object(key: str, data: bytes, content_type: str) -> None:
    await to_thread.run_sync(lambda: put_object_sync(key, data, content_type))


async def delete_object(key: str) -> None:
    await to_thread.run_sync(lambda: delete_object_sync(key))


def presigned_download_url(key: str, file_name: str, expires_in: int) -> str:
    safe_name = file_name.replace('"', "")
    url: str = _public_client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": get_settings().s3_bucket,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{safe_name}"',
        },
        ExpiresIn=expires_in,
    )
    return url
