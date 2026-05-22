from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.security import require_permission
from app.core.database import get_db
from app.models.user import User, UserToken
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/me", summary="Verify admin access")
def admin_me(current_user: User = Depends(require_permission("users:read"))):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": [r.name for r in current_user.roles],
        "permissions": [p.name for role in current_user.roles for p in role.permissions],
    }


@router.get("/stats", summary="Overview stats")
def get_stats(
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    new_users_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar()

    total_conversations = db.query(func.count(Conversation.id)).scalar()
    conversations_today = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= today_start
    ).scalar()

    total_messages = db.query(func.count(Message.id)).scalar()

    total_documents = db.query(func.count(Document.id)).scalar()

    tokens_used_today = db.query(func.sum(UserToken.tokens_used)).scalar() or 0
    total_tokens_ever = db.query(func.sum(UserToken.total_tokens_used)).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "new_today": new_users_today,
        },
        "conversations": {
            "total": total_conversations,
            "today": conversations_today,
        },
        "messages": {
            "total": total_messages,
        },
        "documents": {
            "total": total_documents,
        },
        "tokens": {
            "used_today": tokens_used_today,
            "total_ever": total_tokens_ever,
        },
    }


@router.get("/activity", summary="Recent activity feed")
def get_activity(
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    recent_users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    recent_conversations = (
        db.query(Conversation, User.username)
        .join(User, Conversation.user_id == User.id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "recent_users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "created_at": u.created_at.isoformat(),
            }
            for u in recent_users
        ],
        "recent_conversations": [
            {
                "id": c.id,
                "title": c.title,
                "username": username,
                "created_at": c.created_at.isoformat(),
            }
            for c, username in recent_conversations
        ],
    }
