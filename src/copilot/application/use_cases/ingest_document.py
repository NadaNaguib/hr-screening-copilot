"""Ingest a generic document into the vector store."""
from __future__ import annotations

from uuid import UUID

from copilot.infrastructure.di import Container
from copilot.infrastructure.parsing.parser import parse_document, sha256_bytes


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[tuple[str, int]]:
    words = text.split()
    chunks: list[tuple[str, int]] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append((" ".join(chunk_words), start))
        start = max(end - overlap, start + 1)
    return chunks


async def ingest_document(
    container: Container,
    filename: str,
    content: bytes,
    mime_type: str,
    job_id: UUID | None = None,
    correlation_id: str = "",
) -> dict:
    from copilot.infrastructure.db.models import DocumentORM

    raw_text = parse_document(filename, content, mime_type)
    sha256 = sha256_bytes(content)
    doc = DocumentORM(
        job_id=job_id,
        filename=filename,
        mime_type=mime_type,
        sha256=sha256,
        raw_text=raw_text,
        metadata_={"correlation_id": correlation_id},
    )
    container.session.add(doc)
    await container.session.flush()
    await container.session.refresh(doc)

    chunks = _chunk_text(raw_text)
    chunk_data = [(text, None, {"index": i, "filename": filename}) for i, (text, _) in enumerate(chunks)]
    embeddings = await container.embedding.embed([c[0] for c in chunk_data], correlation_id=correlation_id)
    await container.vector_store.ingest_chunks(
        job_id=job_id,
        document_id=doc.id,
        chunks=chunk_data,
        embeddings=embeddings,
    )
    await container.audit.log(
        action="ingest_document",
        target_type="document",
        target_id=str(doc.id),
        actor_id=None,
        actor_role=None,
        details={"filename": filename, "mime_type": mime_type},
        correlation_id=correlation_id,
    )
    return {"document_id": str(doc.id), "sha256": sha256, "chunks": len(chunks)}
