from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"
    is_incognito: Optional[bool] = False


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    is_incognito: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
