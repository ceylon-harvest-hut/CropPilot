from sqlalchemy.orm import Session

from app.domains.inference.repositories import LlmService
from app.domains.inference.service import InferenceService
from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.loader import DocumentLoader
from app.domains.ingestion.pipeline import DocumentPipeline
from app.domains.ingestion.service import IngestionService
from app.infrastructure.chunkers.dea_gov_lk_chunker import DeaGovLkChunker
from app.infrastructure.chunkers.recursive_chunker import RecursiveChunker
from app.infrastructure.chunkers.section_chunker import SectionChunker
from app.infrastructure.config import Settings
from app.infrastructure.extractors.registry import ExtractorRegistry, build_all_extractors
from app.infrastructure.llm.base_embedder import BaseEmbedder
from app.infrastructure.llm.embeddings import FastEmbedEmbeddingService
from app.infrastructure.loaders.docling_loader import DoclingLoader
from app.infrastructure.loaders.registry import DocumentLoaderRegistry, build_all_loaders
from app.infrastructure.loaders.text_loader import TextLoader
from app.infrastructure.repositories.chroma_retriever import ChromaRetriever
from app.infrastructure.repositories.chroma_store import ChromaVectorStore
from app.infrastructure.repositories.debug_catalog_repo import SqlDebugCatalogRepository
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository


def build_chunker(settings: Settings) -> BaseChunker:
    if settings.default_chunker == "section":
        return SectionChunker()
    if settings.default_chunker == "recursive":
        return RecursiveChunker(
            chunk_size=settings.recursive_chunk_size,
            chunk_overlap=settings.recursive_chunk_overlap,
        )
    raise ValueError(f"Unknown chunker: {settings.default_chunker}")


def build_loader_registry(settings: Settings) -> DocumentLoaderRegistry:
    return DocumentLoaderRegistry(build_all_loaders())


def build_extractor_registry(settings: Settings) -> ExtractorRegistry:
    return ExtractorRegistry(build_all_extractors())


def build_document_pipeline(settings: Settings) -> DocumentPipeline:
    return DocumentPipeline(
        extractors=build_extractor_registry(settings),
        loaders=build_loader_registry(settings),
    )


def build_embedder(settings: Settings) -> BaseEmbedder:
    if settings.embedding_backend == "fast":
        return FastEmbedEmbeddingService()
    raise ValueError(f"Unknown embedding backend: {settings.embedding_backend}")


def build_vector_store(settings: Settings) -> ChromaVectorStore:
    return ChromaVectorStore(persist_directory=settings.chroma_persist_dir)


def build_retriever(settings: Settings) -> ChromaRetriever:
    return ChromaRetriever(
        embedder=build_embedder(settings),
        store=build_vector_store(settings),
    )


def build_llm(settings: Settings) -> LlmService:
    if settings.llm_backend == "gemini":
        from app.infrastructure.llm.chat import GeminiLlmService

        if not settings.google_api_key:
            raise ValueError(
                "Gemini API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env"
            )
        return GeminiLlmService(
            model_name=settings.gemini_model,
            api_key=settings.google_api_key,
        )

    if settings.llm_backend == "ollama":
        from app.infrastructure.llm.chat import OllamaLlmService

        return OllamaLlmService(model_name=settings.ollama_model)

    if settings.llm_backend == "openai":
        from app.infrastructure.llm.chat import OpenAILlmService

        return OpenAILlmService(
            model_name=settings.openai_model,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Unknown LLM backend: {settings.llm_backend}")


def build_inference_service(settings: Settings) -> InferenceService:
    return InferenceService(
        retriever=build_retriever(settings),
        llm=build_llm(settings),
        top_k=settings.retrieval_top_k,
    )


def build_loader_by_name(name: str) -> DocumentLoader:
    loaders = {loader.name: loader for loader in build_all_loaders()}
    loader = loaders.get(name)
    if loader is None:
        known = ", ".join(sorted(loaders))
        raise ValueError(f"Unknown loader: {name!r}. Available: {known}")
    return loader


def build_chunker_by_name(name: str, chunk_size: int = 500, chunk_overlap: int = 50) -> BaseChunker:
    if name == "section":
        return SectionChunker()
    if name == "recursive":
        return RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if name == "dea_gov_lk":
        return DeaGovLkChunker()
    raise ValueError(f"Unknown chunker: {name!r}. Available: section, recursive, dea_gov_lk")


def build_embedder_by_name(name: str) -> BaseEmbedder:
    if name == "fast":
        return FastEmbedEmbeddingService()
    raise ValueError(f"Unknown embedder: {name!r}. Available: fast")


def build_chunk_catalog(settings: Settings) -> ChromaVectorStore:
    return build_vector_store(settings)


def build_source_catalog(session: Session) -> SqlDebugCatalogRepository:
    return SqlDebugCatalogRepository(session)


def build_ingestion_service(settings: Settings, session: Session) -> IngestionService:
    return IngestionService(
        pipeline=build_document_pipeline(settings),
        chunker=build_chunker(settings),
        embedder=build_embedder(settings),
        vector_store=build_vector_store(settings),
        source_repository=SqlKnowledgeSourceRepository(session),
        default_loader=settings.default_loader,
    )
