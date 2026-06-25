from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.domains.ingestion.data import ChunkEmbedding, ChunkMetadata, KnowledgeChunk
from app.domains.lab.dependencies import get_db_session, get_lab_settings
from app.domains.lab.schemas import (
    ChunkItem,
    ChunkRequest,
    ChunkResponse,
    CommitRequest,
    CommitResponse,
    LabOptions,
    LoadRequest,
    LoadResponse,
)
from app.infrastructure.config import Settings
from app.infrastructure.factories import (
    build_chunker_by_name,
    build_embedder_by_name,
    build_loader_by_name,
    build_vector_store,
)
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_INDEXED

router = APIRouter()

AVAILABLE_LOADERS = ["text"]
AVAILABLE_CHUNKERS = ["section", "recursive"]
AVAILABLE_EMBEDDERS = ["fast"]


@router.get("/options", response_model=LabOptions, summary="List available pipeline components")
def get_options() -> LabOptions:
    return LabOptions(
        loaders=AVAILABLE_LOADERS,
        chunkers=AVAILABLE_CHUNKERS,
        embedders=AVAILABLE_EMBEDDERS,
    )


@router.post("/load", response_model=LoadResponse, summary="Load a document with an explicit loader")
def load_document(body: LoadRequest) -> LoadResponse:
    try:
        loader = build_loader_by_name(body.loader)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    try:
        doc = loader.load(body.source_uri)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {body.source_uri}",
        )

    return LoadResponse(
        text=doc.text,
        source_uri=doc.source_uri,
        media_type=doc.media_type,
        char_count=len(doc.text),
        line_count=doc.text.count("\n") + 1,
    )


@router.post("/chunk", response_model=ChunkResponse, summary="Preview chunks without saving")
def preview_chunks(body: ChunkRequest) -> ChunkResponse:
    try:
        chunker = build_chunker_by_name(body.chunker, body.chunk_size, body.chunk_overlap)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    chunks = chunker.chunk(body.text, crop_tag=body.crop_name)

    items = [
        ChunkItem(
            index=i,
            section_name=chunk.metadata.section_name,
            page_number=chunk.metadata.page_number,
            char_count=len(chunk.text_content),
            text=chunk.text_content,
        )
        for i, chunk in enumerate(chunks)
    ]

    return ChunkResponse(chunk_count=len(items), chunks=items)


@router.post(
    "/commit",
    response_model=CommitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Embed chunks and persist to Chroma + SQLite",
)
def commit_chunks(
    body: CommitRequest,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_lab_settings),
) -> CommitResponse:
    if not body.chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No chunks provided to commit",
        )

    try:
        embedder = build_embedder_by_name(body.embedder)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    knowledge_chunks = [
        KnowledgeChunk(
            text_content=item.text,
            metadata=ChunkMetadata(
                section_name=item.section_name,
                page_number=item.page_number,
                crop_tag=body.crop_name,
            ),
        )
        for item in body.chunks
    ]

    knowledge_chunks = embedder.embed(knowledge_chunks)

    vector_store = build_vector_store(settings)
    vector_store.upsert(knowledge_chunks, source_uri=body.source_uri)

    source_repo = SqlKnowledgeSourceRepository(db)
    source_id = source_repo.create_pending(body.source_uri, body.crop_name)
    source_repo.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    return CommitResponse(
        source_id=source_id,
        chunk_count=len(knowledge_chunks),
        status=KNOWLEDGE_SOURCE_STATUS_INDEXED,
    )
