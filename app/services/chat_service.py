from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.conversation_service import ConversationService


class ChatService:

    @staticmethod
    def send_message(
        db: Session,
        conversation_id: int,
        user_id: int,
        content: str,
    ) -> tuple[Message, Message]:
        # Verify ownership
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)

        # Persist user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        db.add(user_message)
        db.flush()

        # Placeholder bot reply — will be replaced with real LLM in Iteration 14
        bot_reply = f"I received your message: \"{content}\"\n\n*(LLM integration coming in Iteration 14)*"

        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=bot_reply,
        )
        db.add(assistant_message)

        # Update conversation timestamp and auto-title on first message
        if conversation.title == "New Chat":
            conversation.title = content[:60] + ("..." if len(content) > 60 else "")
        conversation.updated_at = func.now()

        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)

        return user_message, assistant_message
