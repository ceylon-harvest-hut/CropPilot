from __future__ import annotations

from app.domains.ingestion.content import LoaderOptions
from app.domains.ingestion.loader import KnowledgeDocument


def maybe_persist_output(docs: list[KnowledgeDocument], options: LoaderOptions) -> None:
    """Write joined document text to disk when persist is enabled."""
    if not options.persist or options.output_path is None:
        return
    text = "\n\n".join(d.text for d in docs)
    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    options.output_path.write_text(text, encoding="utf-8")
