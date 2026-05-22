from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.security import require_permission
from app.core.database import get_db
from app.models.user import User, UserToken
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.rbac import Role, Permission

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

    total_users        = db.query(func.count(User.id)).scalar()
    active_users       = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    new_users_today    = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar()
    total_conversations= db.query(func.count(Conversation.id)).scalar()
    conversations_today= db.query(func.count(Conversation.id)).filter(Conversation.created_at >= today_start).scalar()
    total_messages     = db.query(func.count(Message.id)).scalar()
    total_documents    = db.query(func.count(Document.id)).scalar()
    tokens_used_today  = db.query(func.sum(UserToken.tokens_used)).scalar() or 0
    total_tokens_ever  = db.query(func.sum(UserToken.total_tokens_used)).scalar() or 0

    return {
        "users":         {"total": total_users, "active": active_users, "new_today": new_users_today},
        "conversations": {"total": total_conversations, "today": conversations_today},
        "messages":      {"total": total_messages},
        "documents":     {"total": total_documents},
        "tokens":        {"used_today": tokens_used_today, "total_ever": total_tokens_ever},
    }


@router.get("/activity", summary="Recent activity feed")
def get_activity(
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_conversations = (
        db.query(Conversation, User.username)
        .join(User, Conversation.user_id == User.id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "recent_users": [
            {"id": u.id, "username": u.username, "email": u.email, "created_at": u.created_at.isoformat()}
            for u in recent_users
        ],
        "recent_conversations": [
            {"id": c.id, "title": c.title, "username": username, "created_at": c.created_at.isoformat()}
            for c, username in recent_conversations
        ],
    }


# ── User Management ────────────────────────────────────────────────────────────

@router.get("/users", summary="Paginated user list")
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by username or email"),
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if search:
        term = f"%{search}%"
        q = q.filter(or_(User.username.ilike(term), User.email.ilike(term)))

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),  # ceiling division
        "users": [_user_row(u, db) for u in users],
    }


@router.get("/users/{user_id}", summary="User detail")
def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_detail(user, db)


@router.patch("/users/{user_id}/ban", summary="Ban or unban a user")
def toggle_ban(
    user_id: int,
    current_user: User = Depends(require_permission("users:ban")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return {"id": user.id, "is_active": user.is_active}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("users:delete")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Delete in strict dependency order using immediate SQL-level deletes
    conv_ids = db.query(Conversation.id).filter(Conversation.user_id == user_id).subquery()

    # 1. Messages (no DB cascade on conversation_id FK)
    db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
    # 2. Conversations
    db.query(Conversation).filter(Conversation.user_id == user_id).delete(synchronize_session=False)
    # 3. Documents (DB cascade removes document_chunks)
    db.query(Document).filter(Document.user_id == user_id).delete(synchronize_session=False)
    # 4. Token record
    db.query(UserToken).filter(UserToken.user_id == user_id).delete(synchronize_session=False)
    # 5. User (DB cascade removes user_roles)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user_row(user: User, db: Session) -> dict:
    token = db.query(UserToken).filter(UserToken.user_id == user.id).first()
    conv_count = db.query(func.count(Conversation.id)).filter(Conversation.user_id == user.id).scalar()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "gender": user.gender,
        "avatar_seed": user.avatar_seed,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "roles": [r.name for r in user.roles],
        "conversations": conv_count,
        "tokens_used_today": token.tokens_used if token else 0,
        "total_tokens_used": token.total_tokens_used if token else 0,
    }


def _user_detail(user: User, db: Session) -> dict:
    base = _user_row(user, db)
    doc_count = db.query(func.count(Document.id)).filter(Document.user_id == user.id).scalar()
    msg_count = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user.id)
        .scalar()
    )
    base.update({"documents": doc_count, "messages": msg_count})
    return base


# ── Role Management ────────────────────────────────────────────────────────────

class CreateRoleBody(BaseModel):
    name: str
    description: str = ""
    permission_ids: List[int] = []

class AssignRolesBody(BaseModel):
    role_ids: List[int]


@router.get("/roles", summary="List all roles with permissions")
def list_roles(
    current_user: User = Depends(require_permission("roles:assign")),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).order_by(Role.id).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permissions": [{"id": p.id, "name": p.name, "description": p.description} for p in r.permissions],
        }
        for r in roles
    ]


@router.get("/permissions", summary="List all permissions")
def list_permissions(
    current_user: User = Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
):
    perms = db.query(Permission).order_by(Permission.name).all()
    return [{"id": p.id, "name": p.name, "description": p.description} for p in perms]


@router.post("/roles", status_code=status.HTTP_201_CREATED, summary="Create a new role")
def create_role(
    body: CreateRoleBody,
    current_user: User = Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
):
    if db.query(Role).filter(Role.name == body.name).first():
        raise HTTPException(status_code=400, detail="Role name already exists")

    role = Role(name=body.name.lower().strip(), description=body.description)
    if body.permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(body.permission_ids)).all()
        role.permissions = perms
    db.add(role)
    db.commit()
    db.refresh(role)
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": [{"id": p.id, "name": p.name, "description": p.description} for p in role.permissions],
    }


@router.put("/users/{user_id}/roles", summary="Assign roles to a user")
def assign_roles(
    user_id: int,
    body: AssignRolesBody,
    current_user: User = Depends(require_permission("roles:assign")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own roles")

    roles = db.query(Role).filter(Role.id.in_(body.role_ids)).all()
    user.roles = roles
    db.commit()
    db.refresh(user)
    return {"id": user.id, "roles": [r.name for r in user.roles]}
