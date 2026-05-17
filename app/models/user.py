from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    google_id = Column(String(100), unique=True, nullable=True)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    daily_quota = Column(Integer, default=100000)  # 100k tokens per day
    tokens_used = Column(Integer, default=0)
    last_reset = Column(DateTime(timezone=True), server_default=func.now())
    total_tokens_used = Column(BigInteger, default=0)