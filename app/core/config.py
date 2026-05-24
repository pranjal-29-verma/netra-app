from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60   # override in .env (e.g. 480 for 8h)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7      # override in .env

    # Token quota — default for new users; Admin UI override coming in Phase 5
    DEFAULT_DAILY_TOKEN_QUOTA: int = 100000
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str

    # Supabase Storage
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # Voyage AI (embeddings)
    VOYAGE_API_KEY: str

    # LLM — set whichever key matches your chosen provider; LiteLLM reads them automatically
    ANTHROPIC_API_KEY: str | None = None   # claude-*  models
    GEMINI_API_KEY: str | None = None      # gemini/*  models
    OPENAI_API_KEY: str | None = None      # gpt-*     models
    MISTRAL_API_KEY: str | None = None     # mistral-* models
    LLM_MODEL: str = "gemini/gemini-2.0-flash"

    # Fernet key for encrypting LLM API keys stored in DB
    # Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    LLM_ENCRYPTION_KEY: str = "CHANGE_ME_generate_a_real_fernet_key"

    # CORS
    FRONTEND_URL: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]
    
    # App
    PROJECT_NAME: str = "Netra Chatbot"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()