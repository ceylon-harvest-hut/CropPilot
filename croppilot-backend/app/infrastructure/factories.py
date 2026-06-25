from sqlalchemy.orm import Session

from app.domains.ingestion.chunker import BaseChunker, SectionChunkingStrategy
from app.domains.ingestion.service import IngestionService
from app.infrastructure.chunkers.recursive_chunker import RecursiveChunkingStrategy
from app.infrastructure.config import Settings
from app.infrastructure.llm.embeddings import FastEmbedEmbeddingService
from app.infrastructure.loaders.registry import DocumentLoaderRegistry
from app.infrastructure.loaders.text_loader import TextDocumentLoader
from app.infrastructure.repositories.chroma_store import ChromaVectorStore
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository


def build_chunker(settings: Settings) -> BaseChunker:
    if settings.default_chunker == "section":
        return BaseChunker(SectionChunkingStrategy())
    if settings.default_chunker == "recursive":
        return BaseChunker(
            RecursiveChunkingStrategy(
                chunk_size=settings.recursive_chunk_size,
                chunk_overlap=settings.recursive_chunk_overlap,
            )
        )
    raise ValueError(f"Unknown chunker: {settings.default_chunker}")


def build_loader_registry(settings: Settings) -> DocumentLoaderRegistry:
    loaders = [TextDocumentLoader()]
    return DocumentLoaderRegistry(loaders)


def build_embedder(settings: Settings) -> FastEmbedEmbeddingService:
    if settings.embedding_backend == "fast":
        return FastEmbedEmbeddingService()
    raise ValueError(f"Unknown embedding backend: {settings.embedding_backend}")


def build_vector_store(settings: Settings) -> ChromaVectorStore:
    return ChromaVectorStore(persist_directory=settings.chroma_persist_dir)


def build_ingestion_service(settings: Settings, session: Session) -> IngestionService:
    return IngestionService(
        loader_registry=build_loader_registry(settings),
        chunker=build_chunker(settings),
        embedder=build_embedder(settings),
        vector_store=build_vector_store(settings),
        source_repository=SqlKnowledgeSourceRepository(session),
    )
