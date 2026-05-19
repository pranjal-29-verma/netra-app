from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    tokens_used: Optional[int] = None
    sources: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
