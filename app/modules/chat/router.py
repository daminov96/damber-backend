import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.modules.chat import service
from app.modules.chat.schemas import (
    ChatParticipantOut,
    ConversationListOut,
    ConversationSummaryOut,
    MessageListOut,
    MessageOut,
    SendMessageRequest,
    StartConversationRequest,
)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _to_summary_out(summary: service.ConversationSummary) -> ConversationSummaryOut:
    return ConversationSummaryOut(
        id=summary.id,
        listing_id=summary.listing_id,
        listing_name=summary.listing_name,
        other_user=ChatParticipantOut.model_validate(summary.other_user),
        last_message=(
            MessageOut.model_validate(summary.last_message) if summary.last_message else None
        ),
        unread_count=summary.unread_count,
        created_at=summary.created_at,
        is_client=summary.is_client,
    )


@router.post("/conversations", response_model=ConversationSummaryOut, status_code=201)
async def start_conversation(
    payload: StartConversationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    conversation = await service.get_or_create_conversation(db, current_user, payload.listing_id)
    summary = await service.get_conversation_summary(db, conversation.id, current_user)
    return _to_summary_out(summary)


@router.get("/conversations", response_model=ConversationListOut)
async def list_conversations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    summaries, total = await service.list_conversations(db, current_user, page, page_size)
    return ConversationListOut(
        items=[_to_summary_out(s) for s in summaries], total=total, page=page, page_size=page_size
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListOut)
async def list_messages(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    items, total = await service.list_messages(db, conversation_id, current_user, page, page_size)
    return MessageListOut(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=201
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.send_message(db, conversation_id, current_user, payload.text)


@router.post("/conversations/{conversation_id}/read", status_code=204)
async def mark_read(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await service.mark_read(db, conversation_id, current_user)
