from __future__ import annotations

from dataclasses import dataclass

from app.domains.graph.data import ExtractedCropKnowledge
from app.domains.graph.repositories import GraphWriteRepository
from app.domains.ingestion.repositories import KnowledgeSourceRepository
from app.infrastructure.repositories.db import (
    KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_PROCESSING,
)


class SourceAlreadyGraphIngestedError(Exception):
    def __init__(
        self,
        source_id: int,
        graph_node_count: int,
        status: str,
        crop_names: list[str],
    ) -> None:
        self.source_id = source_id
        self.graph_node_count = graph_node_count
        self.status = status
        self.crop_names = crop_names
        super().__init__(f"Source already graph-ingested: {source_id}")


@dataclass
class GraphPersistResult:
    source_id: int
    crop_name: str
    status: str
    replaced: bool = False


def persist_crop_graph(
    *,
    source_uri: str,
    crop_name: str,
    extracted: ExtractedCropKnowledge,
    graph_store: GraphWriteRepository,
    source_repository: KnowledgeSourceRepository,
    replace_existing: bool,
) -> GraphPersistResult:
    existing = source_repository.find_by_origin_url(source_uri)
    replaced = False

    if existing is not None:
        if existing.status == KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED:
            if not replace_existing:
                raise SourceAlreadyGraphIngestedError(
                    source_id=existing.source_id,
                    graph_node_count=graph_store.count_by_source_uri(source_uri),
                    status=existing.status,
                    crop_names=existing.crop_names,
                )
            graph_store.delete_by_source_uri(source_uri)
            replaced = True
            source_id = existing.source_id
        elif replace_existing and graph_store.count_by_source_uri(source_uri) > 0:
            graph_store.delete_by_source_uri(source_uri)
            replaced = True
            source_id = existing.source_id
        else:
            source_id = existing.source_id
    else:
        source_id = source_repository.create_pending(source_uri, crop_name)

    source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_PROCESSING)
    graph_store.upsert_crop(extracted, source_uri=source_uri, crop_tag=crop_name)
    source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED)

    return GraphPersistResult(
        source_id=source_id,
        crop_name=crop_name,
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
        replaced=replaced,
    )
