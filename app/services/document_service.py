import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status
from app.models.document import Document
from app.core.storage import get_storage_client
from app.core.config import settings
from app.services.text_extractor import TextExtractor
from app.services.vector_service import VectorService

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/markdown": "md",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _process_and_index(db: Session, doc: Document, content: bytes | None = None) -> None:
    """Extract text, chunk, embed, and store vectors. Updates doc.status in place."""
    try:
        raw_text = TextExtractor.extract(
            file_type=doc.file_type,
            content=content,
            url=doc.source_url,
        )
        VectorService.store_chunks(db, document_id=doc.id, user_id=doc.user_id, raw_text=raw_text)
        doc.status = "ready"
    except Exception:
        doc.status = "failed"
    db.commit()
    db.refresh(doc)


class DocumentService:

    @staticmethod
    def list_documents(db: Session, user_id: int, conversation_id: int | None = None) -> list[Document]:
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
        file_ext = ALLOWED_TYPES.get(file.content_type)
        if not file_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file.content_type}' not supported. Allowed: PDF, TXT, DOCX, MD",
            )

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File exceeds 20 MB limit",
            )

        storage_path = f"{user_id}/{uuid.uuid4()}.{file_ext}"
        client = get_storage_client()
        client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": file.content_type},
        )

        doc = Document(
            user_id=user_id,
            filename=file.filename or f"upload.{file_ext}",
            file_type=file_ext,
            file_size=len(content),
            storage_path=storage_path,
            status="processing",
            scope=scope,
            conversation_id=conversation_id if scope == "conversation" else None,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        _process_and_index(db, doc, content=content)
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
            status="processing",
            scope=scope,
            conversation_id=conversation_id if scope == "conversation" else None,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        _process_and_index(db, doc)
        return doc

    @staticmethod
    def delete_document(db: Session, document_id: int, user_id: int) -> None:
        doc = db.query(Document).filter(
            Document.id == document_id, Document.user_id == user_id
        ).first()

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        VectorService.delete_chunks(db, document_id)

        if doc.storage_path:
            try:
                client = get_storage_client()
                client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([doc.storage_path])
            except Exception:
                pass

        db.delete(doc)
        db.commit()
