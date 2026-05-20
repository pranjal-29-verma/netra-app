from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, status
from typing import Optional, Literal
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentURLCreate
from app.services.document_service import DocumentService

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
    return await DocumentService.upload_file(db, current_user.id, file, scope, conversation_id)


@router.post("/url", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def add_url(
    body: DocumentURLCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return DocumentService.add_url(db, current_user.id, body.url, body.filename, body.scope, body.conversation_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    DocumentService.delete_document(db, document_id, current_user.id)
