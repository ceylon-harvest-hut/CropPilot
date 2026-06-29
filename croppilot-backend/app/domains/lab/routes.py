from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument
from app.domains.ingestion.persistence import SourceAlreadyIngestedError, persist_knowledge_chunks
from app.domains.lab.dependencies import get_db_session, get_lab_settings
from app.domains.lab.schemas import (
    ChunkItem,
    ChunkerOption,
    ChunkRequest,
    ChunkResponse,
    CommitRequest,
    CommitResponse,
    DocumentItem,
    LabOptions,
    LoadRequest,
    LoadResponse,
    LoaderOption,
    SourceExistsResponse,
)
from app.infrastructure.config import Settings
from app.infrastructure.factories import (
    build_chunker_by_name,
    build_document_pipeline,
    build_embedder_by_name,
    build_vector_store,
)
from app.infrastructure.chunkers.catalog import list_chunker_options
from app.infrastructure.embedders.catalog import list_embedder_names
from app.infrastructure.loaders.catalog import list_loader_options, list_source_types
from app.infrastructure.loaders.validation import LoaderValidationError, validate_source_uri_for_type
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository

router = APIRouter()


def _conflict_detail(exc: SourceAlreadyIngestedError) -> dict:
    return {
        "message": "Source already ingested. Set replace_existing=true to replace vectors.",
        "source_id": exc.source_id,
        "chunk_count": exc.chunk_count,
        "status": exc.status,
        "crop_names": exc.crop_names,
    }


@router.get("/options", response_model=LabOptions, summary="List available pipeline components")
def get_options() -> LabOptions:
    return LabOptions(
        source_types=list_source_types(),
        loaders=[
            LoaderOption(name=opt.name, label=opt.label, source_types=list(opt.source_types))
            for opt in list_loader_options()
        ],
        chunkers=[
            ChunkerOption(name=opt.name, label=opt.label)
            for opt in list_chunker_options()
        ],
        embedders=list_embedder_names(),
    )


@router.get(
    "/sources/exists",
    response_model=SourceExistsResponse,
    summary="Check whether a source URI has already been ingested",
)
def source_exists(
    source_uri: str = Query(..., min_length=1),
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_lab_settings),
) -> SourceExistsResponse:
    source_repo = SqlKnowledgeSourceRepository(db)
    existing = source_repo.find_by_origin_url(source_uri)
    if existing is None:
        return SourceExistsResponse(exists=False)

    vector_store = build_vector_store(settings)
    chunk_count = vector_store.count_by_source_uri(source_uri)
    return SourceExistsResponse(
        exists=True,
        source_id=existing.source_id,
        chunk_count=chunk_count,
        status=existing.status,
        crop_names=existing.crop_names,
    )


@router.post("/load", response_model=LoadResponse, summary="Load a document with an explicit loader")
def load_document(body: LoadRequest, settings: Settings = Depends(get_lab_settings)) -> LoadResponse:
    try:
        validate_source_uri_for_type(body.source_uri, body.source_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    pipeline = build_document_pipeline(settings)

    try:
        docs = pipeline.load_documents(body.source_uri, body.source_type, body.loader)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {body.source_uri}",
        )
    except LoaderValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.as_detail(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    combined_text = "\n\n".join(d.text for d in docs)
    first_meta = docs[0].metadata if docs else {}
    media_type = str(first_meta.get("media_type", "application/octet-stream"))

    return LoadResponse(
        documents=[DocumentItem(text=d.text, metadata=d.metadata) for d in docs],
        source_uri=body.source_uri,
        source_type=body.source_type,
        loader=body.loader,
        media_type=media_type,
        char_count=len(combined_text),
        line_count=combined_text.count("\n") + 1,
    )


@router.post("/chunk", response_model=ChunkResponse, summary="Preview chunks without saving")
def preview_chunks(body: ChunkRequest) -> ChunkResponse:
    try:
        chunker = build_chunker_by_name(body.chunker, body.chunk_size, body.chunk_overlap)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    knowledge_docs = [
        KnowledgeDocument.from_payload(d.text, d.metadata) for d in body.documents
    ]
    chunks = chunker.chunk(knowledge_docs, crop_tag=body.crop_name)

    items = [
        ChunkItem(
            index=i,
            section_name=chunk.metadata.get("section_name", ""),
            page_number=chunk.metadata.get("page_number", 0),
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
        KnowledgeChunk.from_payload(
            text=item.text,
            metadata={
                "crop_tag": body.crop_name,
                "section_name": item.section_name,
                "page_number": item.page_number,
            },
        )
        for item in body.chunks
    ]

    knowledge_chunks = embedder.embed(knowledge_chunks)

    source_repo = SqlKnowledgeSourceRepository(db)
    vector_store = build_vector_store(settings)

    try:
        result = persist_knowledge_chunks(
            source_uri=body.source_uri,
            crop_name=body.crop_name,
            chunks=knowledge_chunks,
            vector_store=vector_store,
            source_repository=source_repo,
            replace_existing=body.replace_existing,
        )
    except SourceAlreadyIngestedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_conflict_detail(exc),
        )

    return CommitResponse(
        source_id=result.source_id,
        chunk_count=result.chunk_count,
        status=result.status,
        replaced=result.replaced,
        previous_chunk_count=result.previous_chunk_count,
    )
