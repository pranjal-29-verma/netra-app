from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.orm import relationship
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
    gender = Column(String(10), nullable=True)        # 'male' | 'female' | 'other'
    avatar_seed = Column(String(100), nullable=True)
    save_conversations = Column(Boolean, default=True)
    theme = Column(String(10), default='system')   # 'light' | 'dark' | 'system'
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(100), nullable=True, unique=True, index=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    roles = relationship("Role", secondary="user_roles", back_populates="users")

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    daily_quota = Column(Integer, default=500)
    tokens_used = Column(Integer, default=0)
    last_reset = Column(DateTime(timezone=True), server_default=func.now())
    total_tokens_used = Column(BigInteger, default=0)
    bonus_tokens = Column(Integer, default=0)
    welcome_bonus_claimed = Column(Boolean, default=False)
    active_plan_id = Column(Integer, nullable=True)
    plan_expires_at = Column(DateTime(timezone=True), nullable=True)