from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str

    # Supabase Storage
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # Voyage AI (embeddings)
    VOYAGE_API_KEY: str

    # CORS
    FRONTEND_URL: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]
    
    # App
    PROJECT_NAME: str = "Netra Chatbot"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()