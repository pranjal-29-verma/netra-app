from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Token quota
    DEFAULT_DAILY_TOKEN_QUOTA: int = 100000

    # Google OAuth
    GOOGLE_CLIENT_ID: str

    # Supabase Storage
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # Voyage AI (embeddings)
    VOYAGE_API_KEY: str

    # LLM
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    LLM_MODEL: str = "gemini/gemini-2.0-flash"

    # Fernet key for encrypting LLM API keys stored in DB
    # Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    LLM_ENCRYPTION_KEY: str = "CHANGE_ME_generate_a_real_fernet_key"

    # Max concurrent LLM calls — prevents hammering the provider under load
    LLM_MAX_CONCURRENT: int = 5

    # API rate limits (slowapi format: "N/second|minute|hour")
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/minute"
    RATE_LIMIT_GOOGLE: str = "5/minute"
    RATE_LIMIT_REFRESH: str = "10/minute"
    RATE_LIMIT_CHAT: str = "20/minute"

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    WELCOME_BONUS_TOKENS: int = 500
    FREE_TIER_DAILY_QUOTA: int = 500
    FREE_TIER_MAX_CONVERSATIONS: int = 5    # None-equivalent = 0 means unlimited; set high to disable
    FREE_TIER_MAX_DOCUMENTS: int = 2

    # Netra Notify (internal email service)
    NOTIFY_BASE_URL: str = "http://localhost:8001"
    NOTIFY_API_KEY: str = "change-me-in-production"
    NOTIFY_ENABLED: bool = False

    # CORS
    FRONTEND_URL: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]

    # App
    PROJECT_NAME: str = "Netra Chatbot"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()