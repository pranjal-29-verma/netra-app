from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_type: str
    file_size: Optional[int] = None
    source_url: Optional[str] = None
    status: str
    scope: str
    conversation_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentURLCreate(BaseModel):
    url: str
    filename: Optional[str] = None
    scope: Literal["global", "conversation"] = "global"
    conversation_id: Optional[int] = None
