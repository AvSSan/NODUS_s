from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import settings
from app.schemas.attachment import PresignedRequest, PresignedResponse


class AttachmentService:
    def create_presigned_post(self, request: PresignedRequest) -> PresignedResponse:
        attachment_id = str(uuid4())
        expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
        payload = f"{attachment_id}:{request.filename}:{request.content_type}:{expires_at.isoformat()}"
        signature = base64.urlsafe_b64encode(
            hashlib.sha256(payload.encode("utf-8")).digest()
        ).decode("utf-8")
        url = f"{settings.s3_endpoint_url}/{settings.s3_bucket}"
        fields = {
            "key": f"{attachment_id}/{request.filename}",
            "Content-Type": request.content_type,
            "X-Amz-Signature": signature,
        }
        return PresignedResponse(attachment_id=attachment_id, url=url, fields=fields, expires_at=expires_at)
