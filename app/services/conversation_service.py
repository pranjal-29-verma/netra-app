from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate


class ConversationService:

    @staticmethod
    def list_conversations(db: Session, user_id: int, limit: int = 20, offset: int = 0) -> list[Conversation]:
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def create_conversation(db: Session, user_id: int, data: ConversationCreate) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            title=data.title or "New Chat",
            is_incognito=data.is_incognito or False,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_conversation(db: Session, conversation_id: int, user_id: int) -> Conversation:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation

    @staticmethod
    def delete_conversation(db: Session, conversation_id: int, user_id: int) -> None:
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)
        db.delete(conversation)
        db.commit()

    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: int,
        user_id: int,
        limit: int = 10,
        before_id: Optional[int] = None,
    ) -> list[Message]:
        ConversationService.get_conversation(db, conversation_id, user_id)
        q = db.query(Message).filter(Message.conversation_id == conversation_id)
        if before_id is not None:
            q = q.filter(Message.id < before_id)
        # Fetch the most recent `limit` messages, then reverse to chronological order
        messages = q.order_by(Message.id.desc()).limit(limit).all()
        return list(reversed(messages))
