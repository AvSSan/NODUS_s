from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from app.schemas.attachment import PresignedRequest
from app.services.attachments import AttachmentService


def test_presigned_contains_required_fields() -> None:
    service = AttachmentService()
    request = PresignedRequest(filename="voice.ogg", content_type="audio/ogg")
    response = service.create_presigned_post(request)
    assert response.attachment_id
    assert response.url.endswith("attachments")
    assert "key" in response.fields
