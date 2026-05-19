from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.token import TokenUsageResponse
from app.services.token_service import TokenService

router = APIRouter(prefix="/tokens", tags=["Tokens"])


@router.get("/usage", response_model=TokenUsageResponse)
def get_token_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = TokenService.get_usage(db, current_user.id)
    remaining = max(0, record.daily_quota - record.tokens_used)
    usage_percentage = round((record.tokens_used / record.daily_quota) * 100, 1) if record.daily_quota else 0.0

    return TokenUsageResponse(
        tokens_used=record.tokens_used,
        daily_quota=record.daily_quota,
        remaining=remaining,
        usage_percentage=usage_percentage,
        total_tokens_used=record.total_tokens_used,
    )
