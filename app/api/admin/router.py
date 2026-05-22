from fastapi import APIRouter, Depends
from app.core.security import get_current_user, require_permission
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/me", summary="Verify admin access")
def admin_me(current_user: User = Depends(require_permission("users:read"))):
    """Returns the current admin user's basic info. Used by frontend to verify admin access on load."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": [r.name for r in current_user.roles],
        "permissions": [p.name for role in current_user.roles for p in role.permissions],
    }
