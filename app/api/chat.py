from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limit import limiter, _get_user_key
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


class StatelessChatRequest(BaseModel):
    content: str
    history: list[dict] = []


@router.post("/stream")
@limiter.limit(lambda: settings.RATE_LIMIT_CHAT, key_func=_get_user_key)
async def stateless_stream(
    request: Request,
    body: StatelessChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StreamingResponse(
        ChatService.stream_stateless(db, current_user.id, body.content, body.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
