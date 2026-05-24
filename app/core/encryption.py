from cryptography.fernet import Fernet
from app.core.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.LLM_ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
