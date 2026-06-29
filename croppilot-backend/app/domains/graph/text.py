from __future__ import annotations

from app.shared.document.loader import KnowledgeDocument


def prepare_extraction_text(documents: list[KnowledgeDocument]) -> str:
    """Join loaded document parts into a single string for LLM extraction."""
    if not documents:
        return ""
    return "\n\n".join(doc.text for doc in documents if doc.text)
