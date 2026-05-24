from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(Integer, primary_key=True, index=True)
    actor_id     = Column(Integer, nullable=True)       # null if actor later deleted
    actor_name   = Column(String(100), nullable=False)  # denormalized — survives deletion
    action       = Column(String(50), nullable=False)   # e.g. "user.ban"
    target_type  = Column(String(50), nullable=True)    # "user" | "llm_config" | "role" | etc.
    target_id    = Column(String(50), nullable=True)    # ID of affected resource
    target_label = Column(String(200), nullable=True)   # human-readable label
    meta         = Column(JSON, nullable=True)           # extra context dict
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
