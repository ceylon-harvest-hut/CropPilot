from __future__ import annotations

import chromadb

from app.domains.debug.data import StoredChunk
from app.domains.inference.data import RetrievedChunk
from app.domains.ingestion.data import KnowledgeChunk


class ChromaVectorStore:
    def __init__(self, persist_directory: str, collection_name: str = "knowledge_chunks") -> None:
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def upsert(self, chunks: list[KnowledgeChunk], source_uri: str) -> None:
        if not chunks:
            return

        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.chunk_id} is missing an embedding")

        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text_content for chunk in chunks],
            embeddings=[chunk.embedding.vector for chunk in chunks],
            metadatas=[
                {
                    "source_uri": source_uri,
                    "crop_tag": chunk.metadata.get("crop_tag", ""),
                    "section_name": chunk.metadata.get("section_name", ""),
                    "page_number": chunk.metadata.get("page_number", 0),
                }
                for chunk in chunks
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        crop_tag: str | None,
        k: int = 3,
    ) -> list[RetrievedChunk]:
        where = {"crop_tag": crop_tag} if crop_tag else None
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
        )

        chunks: list[RetrievedChunk] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for chunk_id, document, metadata in zip(ids, documents, metadatas):
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text_content=document,
                    section_name=metadata.get("section_name", ""),
                    crop_tag=metadata.get("crop_tag", ""),
                    source_uri=metadata.get("source_uri", ""),
                    page_number=int(metadata.get("page_number", 0)),
                )
            )

        return chunks

    def list_chunks(
        self,
        crop_tag: str | None = None,
        source_uri: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[StoredChunk], int]:
        where = None
        if crop_tag and source_uri:
            where = {"$and": [{"crop_tag": crop_tag}, {"source_uri": source_uri}]}
        elif crop_tag:
            where = {"crop_tag": crop_tag}
        elif source_uri:
            where = {"source_uri": source_uri}

        data = self._collection.get(
            where=where,
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )

        chunks = [
            StoredChunk(
                chunk_id=chunk_id,
                crop_tag=meta.get("crop_tag", ""),
                source_uri=meta.get("source_uri", ""),
                section_name=meta.get("section_name", ""),
                page_number=int(meta.get("page_number", 0)),
                text_preview=document[:150],
            )
            for chunk_id, document, meta in zip(
                data.get("ids", []),
                data.get("documents", []),
                data.get("metadatas", []),
            )
        ]

        total = self._count_chunks(where)
        return chunks, total

    def _count_chunks(self, where: dict | None) -> int:
        if where is None:
            return self._collection.count()
        data = self._collection.get(where=where, include=[])
        return len(data.get("ids", []))

    def count(self) -> int:
        return self._collection.count()

    def count_by_source_uri(self, source_uri: str) -> int:
        data = self._collection.get(where={"source_uri": source_uri}, include=[])
        return len(data.get("ids", []))

    def delete_by_source_uri(self, source_uri: str) -> int:
        data = self._collection.get(where={"source_uri": source_uri}, include=[])
        ids = data.get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)
