from datetime import datetime, timezone, timedelta
from typing import List, Optional
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
from app.models.llm_config import LLMConfig, SystemConfig
from app.models.audit_log import AuditLog
from app.models.billing import Plan, TokenPack, UserSubscription
from app.core.encryption import encrypt, decrypt
from app.services import llm_config_service
from app.services import audit_service

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
    action = "user.ban" if not user.is_active else "user.unban"
    try:
        audit_service.write(db, current_user, action,
            target_type="user", target_id=user.id, target_label=user.username,
            metadata={"is_active": user.is_active})
    except Exception:
        pass
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

    deleted_username = user.username
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
    try:
        audit_service.write(db, current_user, "user.delete",
            target_type="user", target_id=user_id, target_label=deleted_username)
    except Exception:
        pass
    db.commit()


class UpdateQuotaBody(BaseModel):
    daily_quota: int


@router.patch("/users/{user_id}/quota", summary="Override a user's daily token quota")
def update_quota(
    user_id: int,
    body: UpdateQuotaBody,
    current_user: User = Depends(require_permission("users:manage_quota")),
    db: Session = Depends(get_db),
):
    if body.daily_quota < 0:
        raise HTTPException(status_code=400, detail="daily_quota must be >= 0")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if not token:
        token = UserToken(user_id=user_id, daily_quota=body.daily_quota)
        db.add(token)
    else:
        old_quota = token.daily_quota
        token.daily_quota = body.daily_quota
        try:
            audit_service.write(db, current_user, "user.quota_change",
                target_type="user", target_id=user_id, target_label=user.username,
                metadata={"old": old_quota, "new": body.daily_quota})
        except Exception:
            pass

    db.commit()
    db.refresh(token)
    return {"user_id": user_id, "daily_quota": token.daily_quota}


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
        "daily_quota": token.daily_quota if token else 100000,
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
    try:
        audit_service.write(db, current_user, "role.create",
            target_type="role", target_id=role.id, target_label=role.name)
        db.commit()
    except Exception:
        pass
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
    try:
        audit_service.write(db, current_user, "role.assign",
            target_type="user", target_id=user.id, target_label=user.username,
            metadata={"roles": [r.name for r in roles]})
    except Exception:
        pass
    db.commit()
    db.refresh(user)
    return {"id": user.id, "roles": [r.name for r in user.roles]}


# ── Content Oversight ──────────────────────────────────────────────────────────

@router.get("/conversations", summary="All conversations (metadata only)")
def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by title or username"),
    current_user: User = Depends(require_permission("conversations:read_meta")),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Conversation, User.username)
        .join(User, Conversation.user_id == User.id)
    )
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(Conversation.title.ilike(term), User.username.ilike(term))
        )

    total = q.count()
    rows = q.order_by(Conversation.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    result = []
    for conv, username in rows:
        msg_count = db.query(func.count(Message.id)).filter(Message.conversation_id == conv.id).scalar()
        result.append({
            "id": conv.id,
            "title": conv.title,
            "username": username,
            "user_id": conv.user_id,
            "is_incognito": conv.is_incognito,
            "message_count": msg_count,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
        "conversations": result,
    }


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a conversation")
def delete_conversation(
    conv_id: int,
    current_user: User = Depends(require_permission("conversations:delete")),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_title = conv.title
    db.query(Message).filter(Message.conversation_id == conv_id).delete(synchronize_session=False)
    db.delete(conv)
    try:
        audit_service.write(db, current_user, "conversation.delete",
            target_type="conversation", target_id=conv_id, target_label=conv_title)
    except Exception:
        pass
    db.commit()


@router.get("/documents", summary="All documents")
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by filename or username"),
    current_user: User = Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Document, User.username)
        .join(User, Document.user_id == User.id)
    )
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(Document.filename.ilike(term), User.username.ilike(term))
        )

    total = q.count()
    rows = q.order_by(Document.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "scope": doc.scope,
                "source_url": doc.source_url,
                "username": username,
                "user_id": doc.user_id,
                "created_at": doc.created_at.isoformat(),
            }
            for doc, username in rows
        ],
    }


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a document")
def delete_document(
    doc_id: int,
    current_user: User = Depends(require_permission("documents:delete")),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc_name = doc.filename
    db.delete(doc)
    try:
        audit_service.write(db, current_user, "document.delete",
            target_type="document", target_id=doc_id, target_label=doc_name)
    except Exception:
        pass
    db.commit()


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/analytics/registrations", summary="Daily new user registrations — last 30 days")
def analytics_registrations(
    current_user: User = Depends(require_permission("analytics:view")),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=29)
    rows = (
        db.query(func.date(User.created_at).label("date"), func.count(User.id).label("count"))
        .filter(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )
    return [{"date": str(r.date), "count": r.count} for r in rows]


@router.get("/analytics/conversations", summary="Daily new conversations — last 30 days")
def analytics_conversations_daily(
    current_user: User = Depends(require_permission("analytics:view")),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=29)
    rows = (
        db.query(func.date(Conversation.created_at).label("date"), func.count(Conversation.id).label("count"))
        .filter(Conversation.created_at >= since)
        .group_by(func.date(Conversation.created_at))
        .order_by(func.date(Conversation.created_at))
        .all()
    )
    return [{"date": str(r.date), "count": r.count} for r in rows]


@router.get("/analytics/top-users", summary="Top 10 users by total token consumption")
def analytics_top_users(
    current_user: User = Depends(require_permission("analytics:view")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User.username, UserToken.total_tokens_used, UserToken.tokens_used)
        .join(UserToken, User.id == UserToken.user_id)
        .order_by(UserToken.total_tokens_used.desc())
        .limit(10)
        .all()
    )
    return [
        {"username": r.username, "total_tokens": r.total_tokens_used, "today_tokens": r.tokens_used}
        for r in rows
    ]


# ── LLM Model Configuration ────────────────────────────────────────────────────

# Curated list of LiteLLM-supported models grouped by provider
SUPPORTED_MODELS = [
    {"provider": "anthropic", "label": "Anthropic", "models": [
        {"id": "claude-opus-4-7",          "label": "Claude Opus 4.7"},
        {"id": "claude-sonnet-4-6",        "label": "Claude Sonnet 4.6"},
        {"id": "claude-haiku-4-5-20251001","label": "Claude Haiku 4.5"},
    ]},
    {"provider": "google", "label": "Google", "models": [
        {"id": "gemini/gemini-2.5-flash",  "label": "Gemini 2.5 Flash"},
        {"id": "gemini/gemini-2.0-flash",  "label": "Gemini 2.0 Flash"},
        {"id": "gemini/gemini-1.5-pro",    "label": "Gemini 1.5 Pro"},
    ]},
    {"provider": "openai", "label": "OpenAI", "models": [
        {"id": "gpt-4o",                   "label": "GPT-4o"},
        {"id": "gpt-4o-mini",              "label": "GPT-4o Mini"},
        {"id": "gpt-4-turbo",              "label": "GPT-4 Turbo"},
    ]},
    {"provider": "mistral", "label": "Mistral", "models": [
        {"id": "mistral/mistral-large-latest", "label": "Mistral Large"},
        {"id": "mistral/mistral-small-latest", "label": "Mistral Small"},
    ]},
]


class LLMConfigCreate(BaseModel):
    provider: str
    model_name: str
    display_label: Optional[str] = None
    api_key: str


class LLMToggleBody(BaseModel):
    use_custom_llm: bool


def _serialize_config(cfg: LLMConfig) -> dict:
    return {
        "id":            cfg.id,
        "provider":      cfg.provider,
        "model_name":    cfg.model_name,
        "display_label": cfg.display_label,
        "is_active":     cfg.is_active,
        "created_at":    cfg.created_at.isoformat(),
    }


def _get_or_create_sys_config(db: Session) -> SystemConfig:
    sys_cfg = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
    if not sys_cfg:
        sys_cfg = SystemConfig(id=1, use_custom_llm=False)
        db.add(sys_cfg)
        db.commit()
        db.refresh(sys_cfg)
    return sys_cfg


@router.get("/llm/supported-models", summary="Curated list of LiteLLM-supported models")
def get_supported_models(
    current_user: User = Depends(require_permission("manage_models")),
):
    return SUPPORTED_MODELS


@router.get("/llm/settings", summary="Get LLM toggle state and active config")
def get_llm_settings(
    current_user: User = Depends(require_permission("manage_models")),
    db: Session = Depends(get_db),
):
    sys_cfg = _get_or_create_sys_config(db)
    active = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
    configs = db.query(LLMConfig).order_by(LLMConfig.created_at.desc()).all()
    return {
        "use_custom_llm": sys_cfg.use_custom_llm,
        "active_config":  _serialize_config(active) if active else None,
        "configs":        [_serialize_config(c) for c in configs],
        "system_default": {"model": __import__('app.core.config', fromlist=['settings']).settings.LLM_MODEL},
    }


@router.patch("/llm/toggle", summary="Toggle between system default and custom LLM")
def toggle_llm_source(
    body: LLMToggleBody,
    current_user: User = Depends(require_permission("manage_models")),
    db: Session = Depends(get_db),
):
    # Guard: cannot enable custom if no active config exists
    if body.use_custom_llm:
        active = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
        if not active:
            raise HTTPException(
                status_code=400,
                detail="No active model configured. Activate a model config first."
            )

    sys_cfg = _get_or_create_sys_config(db)
    sys_cfg.use_custom_llm = body.use_custom_llm
    try:
        audit_service.write(db, current_user, "llm.toggle",
            metadata={"use_custom_llm": body.use_custom_llm})
    except Exception:
        pass
    db.commit()
    llm_config_service.set_use_custom(body.use_custom_llm)
    return {"use_custom_llm": sys_cfg.use_custom_llm}


@router.post("/llm/configs", status_code=status.HTTP_201_CREATED, summary="Save a new LLM config")
def create_llm_config(
    body: LLMConfigCreate,
    current_user: User = Depends(require_permission("manage_models")),
    db: Session = Depends(get_db),
):
    cfg = LLMConfig(
        provider=body.provider,
        model_name=body.model_name,
        display_label=body.display_label or body.model_name,
        api_key_encrypted=encrypt(body.api_key),
        is_active=False,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    try:
        audit_service.write(db, current_user, "llm.config.create",
            target_type="llm_config", target_id=cfg.id, target_label=cfg.display_label,
            metadata={"provider": cfg.provider, "model_name": cfg.model_name})
        db.commit()
    except Exception:
        pass
    return _serialize_config(cfg)


@router.delete("/llm/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an LLM config")
def delete_llm_config(
    config_id: int,
    current_user: User = Depends(require_permission("manage_models")),
    db: Session = Depends(get_db),
):
    cfg = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    if cfg.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the active config. Activate another config or switch to system default first."
        )
    cfg_label = cfg.display_label
    db.delete(cfg)
    try:
        audit_service.write(db, current_user, "llm.config.delete",
            target_type="llm_config", target_id=config_id, target_label=cfg_label)
    except Exception:
        pass
    db.commit()


@router.post("/llm/configs/{config_id}/activate", summary="Activate an LLM config")
def activate_llm_config(
    config_id: int,
    current_user: User = Depends(require_permission("manage_models")),
    db: Session = Depends(get_db),
):
    cfg = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    # Deactivate all others
    db.query(LLMConfig).filter(LLMConfig.id != config_id).update({"is_active": False})
    cfg.is_active = True
    db.commit()
    db.refresh(cfg)

    # Update in-memory cache
    llm_config_service.set_active_cache(cfg.model_name, decrypt(cfg.api_key_encrypted))
    try:
        audit_service.write(db, current_user, "llm.config.activate",
            target_type="llm_config", target_id=cfg.id, target_label=cfg.display_label,
            metadata={"provider": cfg.provider, "model_name": cfg.model_name})
        db.commit()
    except Exception:
        pass
    return _serialize_config(cfg)


@router.post("/llm/configs/{config_id}/deactivate", summary="Deactivate an LLM config (switches to system default)")
def deactivate_llm_config(
    config_id: int,
    current_user: User = Depends(require_permission("manage_models")),
    db: Session = Depends(get_db),
):
    cfg = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    cfg_label = cfg.display_label
    cfg.is_active = False
    # Also force toggle off so system default is used
    sys_cfg = _get_or_create_sys_config(db)
    sys_cfg.use_custom_llm = False
    try:
        audit_service.write(db, current_user, "llm.config.deactivate",
            target_type="llm_config", target_id=config_id, target_label=cfg_label)
    except Exception:
        pass
    db.commit()

    llm_config_service.clear_active_cache()
    llm_config_service.set_use_custom(False)
    return {"message": "Config deactivated. System default LLM is now in use."}


@router.post("/llm/configs/test", summary="Test an LLM config without saving")
async def test_llm_config(
    body: LLMConfigCreate,
    current_user: User = Depends(require_permission("manage_models")),
):
    import litellm
    try:
        response = await litellm.acompletion(
            model=body.model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            api_key=body.api_key,
            timeout=10,
        )
        return {"success": True, "message": f"Connection successful. Model responded."}
    except litellm.AuthenticationError:
        raise HTTPException(status_code=400, detail="Invalid API key for this model.")
    except litellm.BadRequestError as e:
        raise HTTPException(status_code=400, detail=f"Bad request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Test failed: {str(e)}")


# ── Audit Logs ─────────────────────────────────────────────────────────────────

@router.get("/audit-logs", summary="Paginated, filtered admin audit logs")
def list_audit_logs(
    page:        int = Query(1, ge=1),
    limit:       int = Query(20, ge=1, le=100),
    action:      str = Query("", description="Filter by action type e.g. user.ban"),
    actor:       str = Query("", description="Filter by actor username (partial match)"),
    target_type: str = Query("", description="Filter by target type e.g. user, llm_config"),
    date_from:   str = Query("", description="Filter from date (YYYY-MM-DD)"),
    date_to:     str = Query("", description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(require_permission("audit:view")),
    db: Session = Depends(get_db),
):
    from sqlalchemy import and_
    q = db.query(AuditLog)

    if action:
        q = q.filter(AuditLog.action == action)
    if actor:
        q = q.filter(AuditLog.actor_name.ilike(f"%{actor}%"))
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if date_from:
        try:
            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            pass

    total = q.count()
    logs  = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page":  page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
        "logs": [
            {
                "id":           log.id,
                "actor_id":     log.actor_id,
                "actor_name":   log.actor_name,
                "action":       log.action,
                "target_type":  log.target_type,
                "target_id":    log.target_id,
                "target_label": log.target_label,
                "metadata":     log.meta,
                "created_at":   log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


# ── Billing — Plans ────────────────────────────────────────────────────────────

class PlanBody(BaseModel):
    name: str
    description: str = ""
    price_inr: int
    tokens_per_day: int
    duration_days: int
    max_documents: Optional[int] = None
    max_conversations: Optional[int] = None


@router.get("/billing/plans")
def admin_list_plans(
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    return db.query(Plan).order_by(Plan.created_at.desc()).all()


@router.post("/billing/plans", status_code=status.HTTP_201_CREATED)
def admin_create_plan(
    body: PlanBody,
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    plan = Plan(**body.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/billing/plans/{plan_id}")
def admin_update_plan(
    plan_id: int,
    body: PlanBody,
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    for k, v in body.model_dump().items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/billing/plans/{plan_id}/toggle")
def admin_toggle_plan(
    plan_id: int,
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = not plan.is_active
    db.commit()
    return {"id": plan.id, "is_active": plan.is_active}


# ── Billing — Token Packs ──────────────────────────────────────────────────────

class TokenPackBody(BaseModel):
    name: str
    description: str = ""
    price_inr: int
    bonus_tokens: int


@router.get("/billing/packs")
def admin_list_packs(
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    return db.query(TokenPack).order_by(TokenPack.created_at.desc()).all()


@router.post("/billing/packs", status_code=status.HTTP_201_CREATED)
def admin_create_pack(
    body: TokenPackBody,
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    pack = TokenPack(**body.model_dump())
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


@router.patch("/billing/packs/{pack_id}")
def admin_update_pack(
    pack_id: int,
    body: TokenPackBody,
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    pack = db.query(TokenPack).filter(TokenPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Token pack not found")
    for k, v in body.model_dump().items():
        setattr(pack, k, v)
    db.commit()
    db.refresh(pack)
    return pack


@router.patch("/billing/packs/{pack_id}/toggle")
def admin_toggle_pack(
    pack_id: int,
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    pack = db.query(TokenPack).filter(TokenPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Token pack not found")
    pack.is_active = not pack.is_active
    db.commit()
    return {"id": pack.id, "is_active": pack.is_active}


# ── Billing — Subscriptions ────────────────────────────────────────────────────

@router.get("/billing/subscriptions")
def admin_list_subscriptions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query("", alias="status"),
    current_user: User = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    q = db.query(UserSubscription)
    if status_filter:
        q = q.filter(UserSubscription.status == status_filter)
    total = q.count()
    subs = q.order_by(UserSubscription.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    rows = []
    for s in subs:
        user = db.query(User).filter(User.id == s.user_id).first()
        rows.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": user.username if user else "—",
            "email": user.email if user else "—",
            "item_type": s.item_type,
            "item_name": s.item_name,
            "amount_paid": s.amount_paid,
            "status": s.status,
            "razorpay_order_id": s.razorpay_order_id,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        })

    return {"total": total, "page": page, "limit": limit, "subscriptions": rows}
