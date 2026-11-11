"""Object storage for workspace blobs (Cloudflare R2 / MinIO locally).

Keys are always `ws/<workspace_id>/...`. Signed URLs are short-lived and issued only after a
scope check in the service layer (workspace-scoping skill).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.core.errors import AppError

PRESIGN_PUT_SECONDS = 15 * 60
PRESIGN_GET_SECONDS = 5 * 60


class ObjectStorage(Protocol):
    async def put(self, key: str, body: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def delete_prefix(self, prefix: str) -> int: ...

    async def head_size(self, key: str) -> int: ...

    async def presign_put(self, key: str, content_type: str) -> str: ...

    async def presign_get(self, key: str) -> str: ...

    async def ensure_bucket(self) -> None: ...


@dataclass
class MemoryStorage:
    """In-process store for tests. Keys and bytes only; no network."""

    objects: dict[str, tuple[bytes, str]] = field(default_factory=dict)

    async def put(self, key: str, body: bytes, content_type: str) -> None:
        self.objects[key] = (body, content_type)

    async def get(self, key: str) -> bytes:
        try:
            return self.objects[key][0]
        except KeyError as exc:
            raise AppError("object_not_found", "File not found", 404) from exc

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        keys = [k for k in self.objects if k.startswith(prefix)]
        for k in keys:
            del self.objects[k]
        return len(keys)

    async def head_size(self, key: str) -> int:
        try:
            return len(self.objects[key][0])
        except KeyError as exc:
            raise AppError("object_not_found", "File not found", 404) from exc

    async def presign_put(self, key: str, content_type: str) -> str:
        # Tests use the direct put path; this URL is only a marker.
        return f"memory://put/{quote(key, safe='/')}?ct={quote(content_type)}"

    async def presign_get(self, key: str) -> str:
        if key not in self.objects:
            raise AppError("object_not_found", "File not found", 404)
        return f"memory://get/{quote(key, safe='/')}"

    async def ensure_bucket(self) -> None:
        return None


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket

        def client(endpoint: str | None):
            return boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )

        self._client = client(settings.s3_endpoint_url)
        # Presigned URLs go to the browser, so they must use a public host. Server-side
        # reads and writes stay on the internal endpoint (MinIO on the Compose network).
        self._public_client = client(settings.s3_public_endpoint_url or settings.s3_endpoint_url)

    def _run(self, fn, *args, **kwargs):
        return asyncio.to_thread(fn, *args, **kwargs)

    async def put(self, key: str, body: bytes, content_type: str) -> None:
        await self._run(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        try:
            resp = await self._run(self._client.get_object, Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                raise AppError("object_not_found", "File not found", 404) from exc
            raise

        def _read() -> bytes:
            return resp["Body"].read()

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        await self._run(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def delete_prefix(self, prefix: str) -> int:
        """Delete every object under `prefix` (paginated). Returns count removed."""
        removed = 0
        token: str | None = None
        while True:
            kwargs: dict = {"Bucket": self._bucket, "Prefix": prefix, "MaxKeys": 1000}
            if token:
                kwargs["ContinuationToken"] = token
            resp = await self._run(self._client.list_objects_v2, **kwargs)
            contents = resp.get("Contents") or []
            if contents:
                await self._run(
                    self._client.delete_objects,
                    Bucket=self._bucket,
                    Delete={"Objects": [{"Key": o["Key"]} for o in contents], "Quiet": True},
                )
                removed += len(contents)
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
        return removed

    async def head_size(self, key: str) -> int:
        try:
            resp = await self._run(self._client.head_object, Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NotFound", "NoSuchKey"}:
                raise AppError("object_not_found", "File not found", 404) from exc
            raise
        return int(resp["ContentLength"])

    async def presign_put(self, key: str, content_type: str) -> str:
        return await self._run(
            self._public_client.generate_presigned_url,
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=PRESIGN_PUT_SECONDS,
        )

    async def presign_get(self, key: str) -> str:
        return await self._run(
            self._public_client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=PRESIGN_GET_SECONDS,
        )

    async def ensure_bucket(self) -> None:
        try:
            await self._run(self._client.head_bucket, Bucket=self._bucket)
        except ClientError:
            await self._run(self._client.create_bucket, Bucket=self._bucket)


def build_storage(settings: Settings) -> ObjectStorage:
    if settings.s3_endpoint_url is None or settings.environment == "test":
        return MemoryStorage()
    return S3Storage(settings)
