from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService


class VectorService:

    @staticmethod
    def store_chunks(db: Session, document_id: int, user_id: int, raw_text: str) -> int:
        chunks = ChunkingService.chunk(raw_text)
        if not chunks:
            return 0

        embeddings = EmbeddingService.embed_documents(chunks)

        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            db.add(DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                chunk_index=i,
                content=chunk_text,
                embedding=embedding,
            ))

        db.commit()
        return len(chunks)

    @staticmethod
    def similarity_search(
        db: Session,
        query: str,
        user_id: int,
        conversation_id: int | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        query_embedding = EmbeddingService.embed_query(query)

        scope_filter = """
            AND (d.scope = 'global' OR (d.scope = 'conversation' AND d.conversation_id = :conversation_id))
        """ if conversation_id else "AND d.scope = 'global'"

        sql = text(f"""
            SELECT dc.content, dc.document_id, d.filename, d.file_type, d.source_url,
                   1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.user_id = :user_id
              AND d.status = 'ready'
            {scope_filter}
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        params: dict = {
            "embedding": str(query_embedding),
            "user_id": user_id,
            "top_k": top_k,
        }
        if conversation_id:
            params["conversation_id"] = conversation_id

        rows = db.execute(sql, params).fetchall()

        # Deduplicate by content at search time.
        # A user can upload the same file under different scopes (global + conversation),
        # which creates separate document records and separate chunk rows in the DB.
        # Without this, Claude would receive the same text twice in its context window,
        # wasting tokens and potentially confusing the model.
        #
        # FUTURE OPTIMIZATION — content hashing at upload time:
        # Store an MD5/SHA256 hash of the file bytes (or URL content) in the documents
        # table. Before running the embedding pipeline, check if another document with
        # the same hash already exists for this user. If so, reuse its chunk rows
        # instead of re-embedding. This eliminates duplicate rows in document_chunks
        # entirely, saving Voyage AI API quota and keeping the DB lean.
        # Implement this when the document library grows large enough to matter.
        seen: set[str] = set()
        results = []
        for r in rows:
            if r.content not in seen:
                seen.add(r.content)
                results.append({
                    "content": r.content,
                    "document_id": r.document_id,
                    "filename": r.filename,
                    "file_type": r.file_type,
                    "source_url": r.source_url,
                    "similarity": float(r.similarity),
                })
        return results

    @staticmethod
    def delete_chunks(db: Session, document_id: int) -> None:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.commit()
