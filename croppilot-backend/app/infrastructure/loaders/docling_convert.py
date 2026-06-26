from __future__ import annotations

from typing import Any


def docling_load_markdown(file_path: str) -> list[Any]:
    """Run Docling on a local file and return raw LangChain documents as Markdown."""
    from langchain_docling import DoclingLoader  # noqa: PLC0415
    from langchain_docling.loader import ExportType  # noqa: PLC0415

    return DoclingLoader(
        file_path=file_path,
        export_type=ExportType.MARKDOWN,
    ).load()
