from app.domains.ingestion.data import ChunkMetadata, KnowledgeChunk
from app.infrastructure.llm.embeddings import FastEmbedEmbeddingService


def test_embed_assigns_vectors_to_chunks() -> None:
    embedder = FastEmbedEmbeddingService()
    chunks = [
        KnowledgeChunk(
            text_content="Pepper is a widely grown spice.",
            metadata=ChunkMetadata(section_name="History", page_number=0, crop_tag="Pepper"),
        ),
        KnowledgeChunk(
            text_content="Planting spacing is 2.4m x 2.4m.",
            metadata=ChunkMetadata(
                section_name="Crop establishment",
                page_number=0,
                crop_tag="Pepper",
            ),
        ),
    ]

    result = embedder.embed(chunks)

    assert len(result) == 2
    assert all(chunk.embedding is not None for chunk in result)
    assert all(len(chunk.embedding.vector) > 0 for chunk in result)
