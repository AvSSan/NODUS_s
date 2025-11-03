from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.utils import require_idempotency
from app.schemas.attachment import PresignedRequest, PresignedResponse
from app.services.attachments import AttachmentService
from app.services.idempotency import IdempotencyService

router = APIRouter()


@router.post("", response_model=PresignedResponse)
async def create_presigned_attachment(
    payload: PresignedRequest,
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
) -> PresignedResponse:
    key, service = idempotency
    attachment_service = AttachmentService()
    response = attachment_service.create_presigned_post(payload)
    await service.mark_completed(key)
    return response
