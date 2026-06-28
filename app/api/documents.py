from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from typing import Optional, Literal
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentURLCreate
from app.services.document_service import DocumentService
from app.services.billing_service import get_user_limits


def _check_document_limit(db: Session, current_user: User) -> None:
    if any(r.name == "admin" for r in current_user.roles):
        return
    limits = get_user_limits(db, current_user.id)
    max_docs = limits["max_documents"]
    if max_docs is not None:
        count = db.query(Document).filter(Document.user_id == current_user.id).count()
        if count >= max_docs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Document limit reached ({max_docs}). Upgrade your plan to upload more.",
            )

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    conversation_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return DocumentService.list_documents(db, current_user.id, conversation_id)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    scope: Literal["global", "conversation"] = Form("global"),
    conversation_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_document_limit(db, current_user)
    return await DocumentService.upload_file(db, current_user.id, file, scope, conversation_id)


@router.post("/url", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def add_url(
    body: DocumentURLCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_document_limit(db, current_user)
    return DocumentService.add_url(db, current_user.id, body.url, body.filename, body.scope, body.conversation_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    DocumentService.delete_document(db, document_id, current_user.id)
