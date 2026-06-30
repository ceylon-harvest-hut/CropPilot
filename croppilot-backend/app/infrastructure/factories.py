from pathlib import Path

from sqlalchemy.orm import Session

from app.domains.debug.repositories import ChunkCatalogRepository
from app.domains.inference.repositories import RetrieverRepository
from app.shared.llm import LlmClient
from app.domains.inference.service import InferenceService
from app.domains.vector.repositories import KnowledgeVectorRepository
from app.domains.ingestion.chunker import BaseChunker
from app.shared.document.loader import DocumentLoader
from app.shared.document.pipeline import DocumentPipeline
from app.domains.ingestion.service import IngestionService
from app.domains.graph.repositories import GraphExtractionService, GraphWriteRepository
from app.domains.graph.service import GraphIngestionService
from app.domains.agent.service import AgentService
from app.infrastructure.chunkers.dea_gov_lk_chunker import DeaGovLkChunker
from app.infrastructure.chunkers.dea_gov_lk_si_chunker import DeaGovLkSiChunker
from app.infrastructure.chunkers.doa_hordi_chunker import DoaHordiChunker
from app.infrastructure.chunkers.dea_hybrid_chunker import (
    DEFAULT_HYBRID_MAX_CHUNK_SIZE,
    DeaHybridChunker,
)
from app.infrastructure.chunkers.recursive_chunker import RecursiveChunker
from app.infrastructure.chunkers.section_chunker import SectionChunker
from app.infrastructure.config import Settings
from app.infrastructure.extractors.registry import ExtractorRegistry, build_all_extractors
from app.infrastructure.embedders.base import BaseEmbedder
from app.infrastructure.embedders.catalog import list_embedder_names
from app.infrastructure.embedders.fastembed_bge import FastEmbedBGEEmbedder
from app.infrastructure.embedders.fastembed_e5 import FastEmbedE5Embedder
from app.infrastructure.embedders.cache import resolve_cache_dir
from app.infrastructure.loaders.docling_loader import DoclingLoader
from app.infrastructure.loaders.registry import DocumentLoaderRegistry, build_all_loaders
from app.infrastructure.loaders.text_loader import TextLoader
from app.infrastructure.repositories.chroma_store import ChromaVectorStore
from app.infrastructure.repositories.debug_catalog_repo import SqlDebugCatalogRepository
from app.infrastructure.repositories.embedding_retriever import EmbeddingRetriever
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
    cache_dir = resolve_cache_dir(settings.fastembed_cache_dir)
    offline = settings.hf_hub_offline
    allow_download = settings.allow_model_download
    if settings.embedding_backend == "bge_small":
        return FastEmbedBGEEmbedder(
            cache_dir=cache_dir, offline=offline, allow_download=allow_download
        )
    if settings.embedding_backend == "e5_multilingual":
        return FastEmbedE5Embedder(
            cache_dir=cache_dir, offline=offline, allow_download=allow_download
        )
    raise ValueError(
        f"Unknown embedding backend: {settings.embedding_backend!r}. "
        f"Available: {', '.join(list_embedder_names())}"
    )


def build_vector_store(settings: Settings) -> KnowledgeVectorRepository:
    if settings.vector_backend == "chroma":
        return ChromaVectorStore(persist_directory=settings.chroma_persist_dir)
    raise ValueError(f"Unknown vector backend: {settings.vector_backend!r}")


def build_retriever(settings: Settings) -> RetrieverRepository:
    return EmbeddingRetriever(
        embedder=build_embedder(settings),
        store=build_vector_store(settings),
    )


def build_llm(settings: Settings) -> LlmClient:
    if settings.llm_backend == "gemini":
        from app.infrastructure.llm.chat import GeminiLlmClient

        if not settings.google_api_key:
            raise ValueError(
                "Gemini API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env"
            )
        return GeminiLlmClient(
            model_name=settings.gemini_model,
            api_key=settings.google_api_key,
        )

    if settings.llm_backend == "ollama":
        from app.infrastructure.llm.chat import OllamaLlmClient

        return OllamaLlmClient(model_name=settings.ollama_model)

    if settings.llm_backend == "openai":
        from app.infrastructure.llm.chat import OpenAILlmClient

        return OpenAILlmClient(
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
    if name == "dea_gov_lk_si":
        return DeaGovLkSiChunker()
    if name == "doa_hordi":
        return DoaHordiChunker()
    if name == "dea_hybrid":
        max_size = chunk_size if chunk_size != 500 else DEFAULT_HYBRID_MAX_CHUNK_SIZE
        return DeaHybridChunker(max_chunk_size=max_size, chunk_overlap=chunk_overlap)
    raise ValueError(
        f"Unknown chunker: {name!r}. Available: section, recursive, dea_gov_lk, dea_gov_lk_si, doa_hordi, dea_hybrid"
    )


def build_embedder_by_name(name: str, cache_dir: Path | None = None) -> BaseEmbedder:
    if name in ("fast", "bge_small"):  # "fast" kept as backward-compat alias for bge_small
        return FastEmbedBGEEmbedder(cache_dir=cache_dir)
    if name == "e5_multilingual":
        return FastEmbedE5Embedder(cache_dir=cache_dir)
    raise ValueError(
        f"Unknown embedder: {name!r}. Available: {', '.join(list_embedder_names())}"
    )


def build_chunk_catalog(settings: Settings) -> ChunkCatalogRepository:
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


def build_graph_extractor(settings: Settings) -> GraphExtractionService:
    if settings.llm_backend != "gemini":
        raise ValueError(
            f"Graph extraction requires llm_backend=gemini; got {settings.llm_backend!r}"
        )
    if not settings.google_api_key:
        raise ValueError(
            "Gemini API key required for graph extraction. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env"
        )
    from app.infrastructure.graph.llm_crop_extractor import LlmCropGraphExtractor

    return LlmCropGraphExtractor(
        build_llm(settings),
        max_retries=settings.llm_max_retries,
        retry_backoff=settings.llm_retry_backoff_seconds,
    )


def build_neo4j_driver(settings: Settings):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def build_graph_store(settings: Settings) -> GraphWriteRepository:
    from app.infrastructure.graph.neo4j_store import Neo4jGraphStore

    return Neo4jGraphStore(build_neo4j_driver(settings))


def build_graph_read_store(settings: Settings):
    from app.infrastructure.graph.neo4j_read_store import Neo4jGraphReadStore

    return Neo4jGraphReadStore(build_neo4j_driver(settings))


def build_agent_client(settings: Settings):
    from app.domains.agent.service import AgentClient
    from app.infrastructure.agent.gemini_agent_client import GeminiAgentClient
    from app.infrastructure.agent.openai_agent_client import OpenAIAgentClient
    from app.infrastructure.agent.tools.spacing import build_spacing_langchain_tool

    tools = [build_spacing_langchain_tool(build_neo4j_driver(settings))]

    if settings.llm_backend == "gemini":
        if not settings.google_api_key:
            raise ValueError(
                "Gemini API key required for ask agent. "
                "Set GOOGLE_API_KEY or GEMINI_API_KEY in .env"
            )
        return GeminiAgentClient(
            api_key=settings.google_api_key,
            model=settings.gemini_model,
            tools=tools,
        )

    if settings.llm_backend == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key required for ask agent. Set OPENAI_API_KEY in .env"
            )
        return OpenAIAgentClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            tools=tools,
        )

    raise ValueError(
        f"Ask agent supports llm_backend=gemini or openai only; got {settings.llm_backend!r}"
    )


def build_agent_service(settings: Settings) -> AgentService:
    return AgentService(client=build_agent_client(settings))


def build_graph_ingestion_service(settings: Settings, session: Session) -> GraphIngestionService:
    return GraphIngestionService(
        pipeline=build_document_pipeline(settings),
        extractor=build_graph_extractor(settings),
        graph_store=build_graph_store(settings),
        source_repository=SqlKnowledgeSourceRepository(session),
        default_loader=settings.default_loader,
    )
