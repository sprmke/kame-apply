from typing import Any

import pytest

from app.core.config import Settings
from app.core.storage import S3Storage


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "s3_endpoint_url": "http://minio:9000",
        "s3_public_endpoint_url": None,
        "s3_access_key": "key",
        "s3_secret_key": "secret",
        "s3_bucket": "bucket",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_presigned_urls_use_the_public_endpoint() -> None:
    store = S3Storage(_settings(s3_public_endpoint_url="https://s3.example.com"))

    url = await store.presign_get("ws/w/file.pdf")

    assert url.startswith("https://s3.example.com/bucket/ws/w/file.pdf")


@pytest.mark.asyncio
async def test_presigned_urls_default_to_the_internal_endpoint() -> None:
    store = S3Storage(_settings())

    url = await store.presign_get("ws/w/file.pdf")

    assert url.startswith("http://minio:9000/bucket/ws/w/file.pdf")
