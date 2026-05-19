import uuid
import os
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status
from app.models.document import Document
from app.core.storage import get_storage_client
from app.core.config import settings

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/markdown": "md",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class DocumentService:

    @staticmethod
    def list_documents(db: Session, user_id: int, conversation_id: int | None = None) -> list[Document]:
        """
        Returns global docs + conversation-scoped docs for the given conversation.
        If no conversation_id provided, returns only global docs.
        """
        query = db.query(Document).filter(Document.user_id == user_id)

        if conversation_id:
            query = query.filter(
                (Document.scope == "global") |
                ((Document.scope == "conversation") & (Document.conversation_id == conversation_id))
            )
        else:
            query = query.filter(Document.scope == "global")

        return query.order_by(Document.created_at.desc()).all()

    @staticmethod
    async def upload_file(
        db: Session,
        user_id: int,
        file: UploadFile,
        scope: str = "global",
        conversation_id: int | None = None,
    ) -> Document:
        # Validate type
        file_ext = ALLOWED_TYPES.get(file.content_type)
        if not file_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file.content_type}' not supported. Allowed: PDF, TXT, DOCX, MD",
            )

        # Read and validate size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File exceeds 20 MB limit",
            )

        # Build unique storage path
        storage_path = f"{user_id}/{uuid.uuid4()}.{file_ext}"

        # Upload to Supabase Storage
        client = get_storage_client()
        client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": file.content_type},
        )

        # Save record to DB
        doc = Document(
            user_id=user_id,
            filename=file.filename or f"upload.{file_ext}",
            file_type=file_ext,
            file_size=len(content),
            storage_path=storage_path,
            status="ready",
            scope=scope,
            conversation_id=conversation_id if scope == "conversation" else None,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def add_url(
        db: Session,
        user_id: int,
        url: str,
        filename: str | None,
        scope: str = "global",
        conversation_id: int | None = None,
    ) -> Document:
        label = filename or url.split("/")[-1] or "link"
        doc = Document(
            user_id=user_id,
            filename=label[:255],
            file_type="url",
            source_url=url,
            status="ready",
            scope=scope,
            conversation_id=conversation_id if scope == "conversation" else None,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def delete_document(db: Session, document_id: int, user_id: int) -> None:
        doc = db.query(Document).filter(
            Document.id == document_id, Document.user_id == user_id
        ).first()

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Remove from Supabase Storage if it has a stored file
        if doc.storage_path:
            try:
                client = get_storage_client()
                client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([doc.storage_path])
            except Exception:
                pass  # Don't fail the delete if storage removal fails

        db.delete(doc)
        db.commit()
