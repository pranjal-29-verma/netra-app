from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)   # pdf, txt, docx, url
    file_size = Column(BigInteger, nullable=True)     # bytes; null for URLs
    storage_path = Column(String(500), nullable=True) # Supabase storage path; null for URLs
    source_url = Column(String(2000), nullable=True)  # original URL if type=url
    status = Column(String(20), nullable=False, default="ready")  # ready | processing | failed
    scope = Column(String(20), nullable=False, default="global")  # global | conversation
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
