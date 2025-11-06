from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_session
from app.api.utils import require_idempotency
from app.repositories.attachment import AttachmentRepository
from app.schemas.attachment import (
    AttachmentCreate,
    AttachmentResponse,
    PresignedRequest,
    PresignedResponse,
)
from app.services.attachments import AttachmentService
from app.services.idempotency import IdempotencyService

router = APIRouter()


@router.post("/presigned", response_model=PresignedResponse)
async def create_presigned_url(
    payload: PresignedRequest,
    idempotency: tuple[str, IdempotencyService] = Depends(require_idempotency),
    current_user: int = Depends(get_current_user),
) -> PresignedResponse:
    """Создает presigned URL для загрузки файла"""
    key, service = idempotency
    attachment_service = AttachmentService()
    response = attachment_service.create_presigned_post(payload)
    await service.mark_completed(key)
    return response


@router.post("/confirm", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def confirm_attachment_upload(
    payload: AttachmentCreate,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AttachmentResponse:
    """Подтверждает загрузку файла и создает запись в БД"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Confirming upload for attachment_id: {payload.attachment_id}")
    logger.info(f"User: {current_user}, filename: {payload.filename}, size: {payload.size_bytes}")
    
    attachment_service = AttachmentService()
    attachment_repo = AttachmentRepository(session)
    
    try:
        # Формируем storage_key
        storage_key = f"attachments/{payload.attachment_id}/{payload.filename}"
        logger.info(f"Storage key: {storage_key}")
        
        # Создаем запись в БД
        attachment = await attachment_repo.create(
            attachment_id=payload.attachment_id,
            user_id=current_user,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            storage_key=storage_key,
            metadata=payload.metadata,
        )
        logger.info(f"Attachment record created in DB")
        
        await session.commit()
        logger.info(f"Transaction committed")
        
        # Генерируем URL для скачивания
        download_url = attachment_service.get_download_url(
            attachment_id=payload.attachment_id,
            filename=payload.filename,
        )
        logger.info(f"Download URL generated: {download_url[:50]}...")
        
        return AttachmentResponse(
            id=attachment.id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=attachment.size_bytes,
            url=download_url,
            metadata=attachment.meta,
            created_at=attachment.created_at,
        )
    except Exception as e:
        logger.error(f"Error confirming attachment: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm attachment upload: {str(e)}"
        )


@router.get("/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment(
    attachment_id: str,
    current_user: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AttachmentResponse:
    """Получает информацию о вложении"""
    attachment_service = AttachmentService()
    attachment_repo = AttachmentRepository(session)
    
    attachment = await attachment_repo.get_by_id(attachment_id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    
    # Генерируем свежий URL для скачивания
    download_url = attachment_service.get_download_url(
        attachment_id=attachment.id,
        filename=attachment.filename,
    )
    
    return AttachmentResponse(
        id=attachment.id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        url=download_url,
        metadata=attachment.meta,
        created_at=attachment.created_at,
    )
