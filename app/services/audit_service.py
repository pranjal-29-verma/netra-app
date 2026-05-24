"""
Audit logging helper. Call write() after a successful admin action.
Failures here never block the actual action — wrapped in try/except at call sites.
"""
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User


def write(
    db: Session,
    actor: User,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    target_label: str | None = None,
    metadata: dict | None = None,
) -> None:
    log = AuditLog(
        actor_id=actor.id,
        actor_name=actor.username,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        target_label=target_label,
        meta=metadata,
    )
    db.add(log)
    db.flush()  # write in the current transaction — caller commits
