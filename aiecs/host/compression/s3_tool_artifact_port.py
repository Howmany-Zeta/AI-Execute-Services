# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""S3-compatible ToolArtifactPort for host MinIO/S3 (ADR-012, CC-092).

Requires ``boto3`` in the host environment. aiecs core does not depend on boto3;
install in python-middleware or ``pip install boto3`` alongside aiecs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from functools import partial
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_PUT_OBJECT_RETRIES = 3


class S3ToolArtifactPort:
    """Store full tool outputs in S3/MinIO; return URI for inline preview stub."""

    def __init__(
        self,
        *,
        bucket: str | None = None,
        prefix: str = "tool-artifacts",
        endpoint_url: str | None = None,
        region_name: str | None = None,
        client: Any | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        self.bucket = bucket or os.environ.get("AIECS_TOOL_ARTIFACT_BUCKET", "").strip()
        if not self.bucket:
            raise ValueError("S3ToolArtifactPort requires bucket= or AIECS_TOOL_ARTIFACT_BUCKET")
        self.prefix = prefix.strip("/") or "tool-artifacts"
        self._endpoint_url = (
            endpoint_url
            or os.environ.get(
                "AIECS_TOOL_ARTIFACT_ENDPOINT_URL",
                os.environ.get("S3_ENDPOINT_URL", ""),
            ).strip()
            or None
        )
        self._region_name = region_name or os.environ.get(
            "AWS_DEFAULT_REGION",
            "us-east-1",
        )
        self._client = client
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as exc:
            raise ImportError("S3ToolArtifactPort requires boto3. Install in the host: pip install boto3") from exc
        kwargs: dict[str, Any] = {"region_name": self._region_name}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._aws_access_key_id and self._aws_secret_access_key:
            kwargs["aws_access_key_id"] = self._aws_access_key_id
            kwargs["aws_secret_access_key"] = self._aws_secret_access_key
            if self._aws_session_token:
                kwargs["aws_session_token"] = self._aws_session_token
        self._client = boto3.client("s3", **kwargs)
        return self._client

    def _object_key(self, session_id: str, tool_call_id: str) -> str:
        safe_session = session_id.replace("/", "_") or "unknown-session"
        safe_tool = tool_call_id.replace("/", "_") or uuid.uuid4().hex
        return f"{self.prefix}/{safe_session}/{safe_tool}.txt"

    @staticmethod
    @retry(
        stop=stop_after_attempt(_PUT_OBJECT_RETRIES),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _put_object_sync(
        client: Any,
        *,
        bucket: str,
        key: str,
        body: bytes,
    ) -> None:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="text/plain; charset=utf-8",
        )

    async def store_tool_output(
        self,
        *,
        session_id: str,
        tool_call_id: str,
        content: str,
    ) -> str:
        key = self._object_key(session_id, tool_call_id)
        body = content.encode("utf-8")
        client = self._get_client()
        try:
            await asyncio.to_thread(
                partial(
                    self._put_object_sync,
                    client,
                    bucket=self.bucket,
                    key=key,
                    body=body,
                )
            )
        except Exception as exc:
            logger.error(
                "Failed to store tool artifact session=%s tool_call_id=%s key=%s",
                session_id,
                tool_call_id,
                key,
                exc_info=exc,
            )
            raise
        if self._endpoint_url:
            base = self._endpoint_url.rstrip("/")
            uri = f"{base}/{self.bucket}/{key}"
        else:
            uri = f"s3://{self.bucket}/{key}"
        logger.debug(
            "Stored tool artifact session=%s tool_call_id=%s bytes=%d uri=%s",
            session_id,
            tool_call_id,
            len(body),
            uri,
        )
        return uri
