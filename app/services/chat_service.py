import json
from typing import AsyncIterator
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.conversation_service import ConversationService
from app.services.vector_service import VectorService
from app.services.llm_service import stream_response
from app.services.token_service import TokenService

HISTORY_LIMIT = 10  # last N messages sent as conversation context to the LLM


class ChatService:

    @staticmethod
    def _get_history(db: Session, conversation_id: int) -> list[dict]:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_LIMIT)
            .all()
        )
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

    @staticmethod
    async def stream_message(
        db: Session,
        conversation_id: int,
        user_id: int,
        content: str,
    ) -> AsyncIterator[str]:
        # Verify ownership
        conversation = ConversationService.get_conversation(db, conversation_id, user_id)

        # Save user message
        user_message = Message(conversation_id=conversation_id, role="user", content=content)
        db.add(user_message)
        db.flush()
        db.refresh(user_message)

        # Auto-title on first message
        if conversation.title == "New Chat":
            conversation.title = content[:60] + ("..." if len(content) > 60 else "")
        conversation.updated_at = func.now()
        db.commit()

        # RAG: find relevant chunks scoped to this conversation
        chunks = VectorService.similarity_search(
            db, query=content, user_id=user_id,
            conversation_id=conversation_id, top_k=5,
        )

        # Conversation history for multi-turn context
        history = ChatService._get_history(db, conversation_id)

        # Stream LLM response, accumulate full text
        full_response = ""
        sources = [
            {"document_id": c["document_id"], "filename": c["filename"], "file_type": c["file_type"]}
            for c in chunks
        ]

        # Yield user message first so frontend can render it immediately
        yield f"data: {json.dumps({'type': 'user_message', 'message': {'id': user_message.id, 'conversation_id': conversation_id, 'role': 'user', 'content': content, 'created_at': user_message.created_at.isoformat()}})}\n\n"

        try:
            async for delta in stream_response(content, history, chunks):
                full_response += delta
                yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                user_msg = "Rate limit exceeded. Please wait a moment and try again."
            else:
                user_msg = "Failed to generate a response. Please try again."
            yield f"data: {json.dumps({'type': 'error', 'message': user_msg})}\n\n"
            return

        # Count tokens via litellm
        import litellm as _litellm
        from app.core.config import settings as _settings
        try:
            input_tokens = _litellm.token_counter(model=_settings.LLM_MODEL, text=content)
            output_tokens = _litellm.token_counter(model=_settings.LLM_MODEL, text=full_response)
            total_tokens = input_tokens + output_tokens
        except Exception:
            total_tokens = 0

        # Save assistant message
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            tokens_used=total_tokens if total_tokens else None,
            sources=sources if sources else None,
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        # Update token quota
        if total_tokens:
            TokenService.add_tokens(db, user_id, total_tokens)

        yield f"data: {json.dumps({'type': 'done', 'message': {'id': assistant_message.id, 'conversation_id': conversation_id, 'role': 'assistant', 'content': full_response, 'tokens_used': total_tokens or None, 'sources': sources or None, 'created_at': assistant_message.created_at.isoformat()}})}\n\n"

    @staticmethod
    async def stream_stateless(
        db: Session,
        user_id: int,
        content: str,
        history: list[dict],
    ) -> AsyncIterator[str]:
        # RAG: global docs only — incognito has no conversation scope
        chunks = VectorService.similarity_search(
            db, query=content, user_id=user_id,
            conversation_id=None, top_k=5,
        )
        sources = [
            {"document_id": c["document_id"], "filename": c["filename"], "file_type": c["file_type"]}
            for c in chunks
        ]

        try:
            async for delta in stream_response(content, history, chunks):
                yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                user_msg = "Rate limit exceeded. Please wait a moment and try again."
            else:
                user_msg = "Failed to generate a response. Please try again."
            yield f"data: {json.dumps({'type': 'error', 'message': user_msg})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"
