import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.chat.models import Conversation, Message
from app.modules.listings.models import Listing
from app.modules.users.models import User

PHONE_RE = re.compile(r"\d[\d\-\s\(\)]{6,}\d")
CARD_RE = re.compile(r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}")


def _contains_sensitive_data(text: str) -> bool:
    return bool(PHONE_RE.search(text) or CARD_RE.search(text))


def _check_participant(conversation: Conversation, user: User) -> None:
    if user.id not in (conversation.client_id, conversation.owner_id):
        raise ForbiddenError("Bu suhbatga kirish huquqingiz yo'q")


async def _get_conversation_or_404(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise NotFoundError("Suhbat topilmadi")
    return conversation


async def _get_listing_or_404(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise NotFoundError("Listing topilmadi")
    return listing


async def get_or_create_conversation(
    db: AsyncSession, client: User, listing_id: uuid.UUID
) -> Conversation:
    listing = await _get_listing_or_404(db, listing_id)
    if listing.owner_id == client.id:
        raise ConflictError("O'z e'loningizga yoza olmaysiz")

    stmt = select(Conversation).where(
        Conversation.client_id == client.id, Conversation.owner_id == listing.owner_id
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    conversation = Conversation(
        client_id=client.id, owner_id=listing.owner_id, listing_id=listing.id
    )
    db.add(conversation)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        conversation = (await db.execute(stmt)).scalar_one()
    else:
        await db.refresh(conversation)
    return conversation


@dataclass
class ConversationSummary:
    id: uuid.UUID
    listing_id: uuid.UUID | None
    listing_name: str | None
    other_user: User
    last_message: Message | None
    unread_count: int
    created_at: datetime
    is_client: bool


async def _build_summary(
    db: AsyncSession, conversation: Conversation, user: User
) -> ConversationSummary:
    other_user_id = (
        conversation.owner_id if user.id == conversation.client_id else conversation.client_id
    )
    other_user = await db.get(User, other_user_id)

    listing_name = None
    if conversation.listing_id:
        listing = await db.get(Listing, conversation.listing_id)
        if listing:
            listing_name = listing.name

    last_message = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    unread_count = (
        await db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.sender_id != user.id,
                Message.read_at.is_(None),
            )
        )
    ).scalar_one()

    return ConversationSummary(
        id=conversation.id,
        listing_id=conversation.listing_id,
        listing_name=listing_name,
        other_user=other_user,
        last_message=last_message,
        unread_count=unread_count,
        created_at=conversation.created_at,
        is_client=user.id == conversation.client_id,
    )


async def get_conversation_summary(
    db: AsyncSession, conversation_id: uuid.UUID, user: User
) -> ConversationSummary:
    conversation = await _get_conversation_or_404(db, conversation_id)
    _check_participant(conversation, user)
    return await _build_summary(db, conversation, user)


async def list_conversations(
    db: AsyncSession, user: User, page: int, page_size: int
) -> tuple[list[ConversationSummary], int]:
    conditions = or_(Conversation.client_id == user.id, Conversation.owner_id == user.id)

    count_stmt = select(func.count()).select_from(Conversation).where(conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    last_message_time = (
        select(func.max(Message.created_at))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    stmt = (
        select(Conversation)
        .where(conditions)
        .order_by(func.coalesce(last_message_time, Conversation.created_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    conversations = list((await db.execute(stmt)).scalars().all())

    summaries = [await _build_summary(db, conversation, user) for conversation in conversations]
    return summaries, total


async def list_messages(
    db: AsyncSession, conversation_id: uuid.UUID, user: User, page: int, page_size: int
) -> tuple[list[Message], int]:
    conversation = await _get_conversation_or_404(db, conversation_id)
    _check_participant(conversation, user)

    count_stmt = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def send_message(
    db: AsyncSession, conversation_id: uuid.UUID, user: User, text: str
) -> Message:
    conversation = await _get_conversation_or_404(db, conversation_id)
    _check_participant(conversation, user)
    if _contains_sensitive_data(text):
        raise HTTPException(
            400,
            detail="Xabarda shaxsiy aloqa ma'lumotlari (telefon/karta raqami) bo'lishi mumkin emas",
        )

    message = Message(conversation_id=conversation_id, sender_id=user.id, text=text)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def mark_read(db: AsyncSession, conversation_id: uuid.UUID, user: User) -> None:
    conversation = await _get_conversation_or_404(db, conversation_id)
    _check_participant(conversation, user)

    stmt = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.sender_id != user.id,
        Message.read_at.is_(None),
    )
    unread_messages = (await db.execute(stmt)).scalars().all()
    for message in unread_messages:
        message.read_at = func.now()
    await db.commit()
