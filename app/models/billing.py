from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_inr = Column(Integer, nullable=False)          # full rupees (e.g. 20)
    tokens_per_day = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    max_documents = Column(Integer, nullable=True)       # None = unlimited
    max_conversations = Column(Integer, nullable=True)   # None = unlimited
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TokenPack(Base):
    __tablename__ = "token_packs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_inr = Column(Integer, nullable=False)          # full rupees
    bonus_tokens = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    item_type = Column(String(20), nullable=False)       # 'plan' | 'pack'
    item_id = Column(Integer, nullable=False)
    item_name = Column(String(100), nullable=False)
    amount_paid = Column(Integer, nullable=False)        # in paise
    razorpay_order_id = Column(String(100), nullable=False, unique=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    status = Column(String(20), default='pending')       # pending | paid | failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)   # plans only
    created_at = Column(DateTime(timezone=True), server_default=func.now())
