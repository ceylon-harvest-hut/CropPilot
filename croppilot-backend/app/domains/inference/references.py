"""Build labeled RAG context and grouped reference documents from retrieved chunks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.domains.inference.data import RetrievedChunk
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL, infer_source_type

EXCERPT_MAX_LENGTH = 200


@dataclass(frozen=True)
class ReferenceDocument:
    source_uri: str
    crop_name: str
    title: str
    excerpt: str
    source_type: str


def reference_title(crop_name: str, source_uri: str) -> str:
    if crop_name:
        return crop_name
    parsed = urlparse(source_uri)
    if parsed.scheme in ("http", "https"):
        slug = parsed.path.strip("/").split("/")[-1] if parsed.path.strip("/") else parsed.netloc
        return slug.replace("-", " ").title() if slug else source_uri
    return Path(source_uri).stem.replace("-", " ").title()


def build_rag_context(
    chunks: list[RetrievedChunk],
) -> tuple[str, list[ReferenceDocument]]:
    """Group chunks by source URI and produce labeled context for the LLM."""
    if not chunks:
        return "", []

    groups: dict[str, list[RetrievedChunk]] = {}
    order: list[str] = []
    for chunk in chunks:
        uri = chunk.source_uri or "unknown"
        if uri not in groups:
            order.append(uri)
            groups[uri] = []
        groups[uri].append(chunk)

    context_parts: list[str] = []
    references: list[ReferenceDocument] = []

    for uri in order:
        doc_chunks = groups[uri]
        crop_name = doc_chunks[0].crop_tag
        source_type = infer_source_type(uri) if uri != "unknown" else SOURCE_TYPE_FILE
        title = reference_title(crop_name, uri)
        excerpt = _trim_excerpt(doc_chunks[0].text_content)

        header = f"--- {title} ---\nSource: {uri}"

        body_parts: list[str] = []
        for chunk in doc_chunks:
            if chunk.section_name:
                body_parts.append(f"### {chunk.section_name}\n{chunk.text_content}")
            else:
                body_parts.append(chunk.text_content)

        context_parts.append(f"{header}\n" + "\n\n".join(body_parts))
        references.append(
            ReferenceDocument(
                source_uri=uri,
                crop_name=crop_name,
                title=title,
                excerpt=excerpt,
                source_type=source_type,
            )
        )

    return "\n\n".join(context_parts), references


def _trim_excerpt(text: str, max_length: int = EXCERPT_MAX_LENGTH) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 1].rstrip() + "…"
