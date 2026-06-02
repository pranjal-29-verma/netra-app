from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.security import verify_token


def _get_user_key(request: Request) -> str:
    """Per-user key for chat endpoints — falls back to IP if unauthenticated."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = verify_token(auth[7:])
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


# Single limiter — key_func can be overridden per route via @limiter.limit(..., key_func=...)
limiter = Limiter(key_func=get_remote_address)
