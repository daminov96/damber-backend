import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StartConversationRequest(BaseModel):
    listing_id: uuid.UUID


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    surname: str
    avatar_url: str | None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    text: str
    created_at: datetime
    read_at: datetime | None


class MessageListOut(BaseModel):
    items: list[MessageOut]
    total: int
    page: int
    page_size: int


class ConversationSummaryOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID | None
    other_user: ChatParticipantOut
    last_message: MessageOut | None
    unread_count: int
    created_at: datetime


class ConversationListOut(BaseModel):
    items: list[ConversationSummaryOut]
    total: int
    page: int
    page_size: int
