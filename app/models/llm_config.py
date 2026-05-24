from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id               = Column(Integer, primary_key=True, index=True)
    provider         = Column(String(50), nullable=False)   # anthropic | openai | google | mistral
    model_name       = Column(String(100), nullable=False)  # litellm model string
    display_label    = Column(String(100), nullable=True)   # human-readable name
    api_key_encrypted= Column(Text, nullable=False)
    is_active        = Column(Boolean, default=False, nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class SystemConfig(Base):
    """Singleton row (id=1) that stores system-wide toggles."""
    __tablename__ = "system_config"

    id             = Column(Integer, primary_key=True, default=1)
    use_custom_llm = Column(Boolean, default=False, nullable=False)
