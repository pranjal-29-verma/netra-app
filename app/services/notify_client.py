"""
HTTP client for netra-notify service.

All calls are fire-and-forget — run them via FastAPI BackgroundTasks so they
never block the main request. If netra-notify is down, the error is logged
and the user flow continues normally.
"""
import logging
import urllib.request
import urllib.error
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "Content-Type": "application/json",
    "X-Api-Key": settings.NOTIFY_API_KEY,
}


def _post(path: str, payload: dict) -> None:
    if not settings.NOTIFY_ENABLED:
        logger.info(f"[notify disabled] POST {path} payload={payload}")
        return
    url = f"{settings.NOTIFY_BASE_URL}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
        logger.info(f"[notify] POST {path} → ok")
    except urllib.error.URLError as exc:
        logger.error(f"[notify] POST {path} failed: {exc}")


def send_verification_email(to_email: str, username: str, token: str) -> None:
    _post("/send/verification", {"to_email": to_email, "username": username, "token": token})


def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    _post("/send/password-reset", {"to_email": to_email, "username": username, "token": token})


def send_announcement_email(to_emails: list[str], subject: str, body: str) -> None:
    _post("/send/announcement", {"to_emails": to_emails, "subject": subject, "body": body})
