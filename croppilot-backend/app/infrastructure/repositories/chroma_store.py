from __future__ import annotations

import chromadb

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
                    "crop_tag": chunk.metadata.crop_tag,
                    "section_name": chunk.metadata.section_name,
                    "page_number": chunk.metadata.page_number,
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
                )
            )

        return chunks

    def count(self) -> int:
        return self._collection.count()
