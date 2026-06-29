"""Chunker for KnowledgeDocuments produced by DeaGovLkLoader.

Each document already represents one semantic section (e.g. "History",
"Soils and Climatic needs"). The chunker:

1. Emits the full section as a single chunk when it is short enough.
2. Splits longer sections at ``**Bold Header**`` lines that the loader
   embedded from ``<strong>`` tags — those are natural sub-section
   boundaries inside a section.
3. Never splits Markdown tables (``|``-delimited blocks) across chunks.

All ``KnowledgeChunk`` metadata inherits ``crop_name``, ``scientific_name``,
``family`` and ``section_name`` from the source document.
"""

from __future__ import annotations

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument

LONG_SECTION_THRESHOLD = 1200  # characters


class DeaGovLkChunker(BaseChunker):
    """Produce KnowledgeChunks from DeaGovLkLoader output.

    Parameters
    ----------
    long_section_threshold:
        Character count above which a section is split further at bold-header
        markers.  Defaults to ``LONG_SECTION_THRESHOLD``.
    """

    name = "dea_gov_lk"

    def __init__(self, long_section_threshold: int = LONG_SECTION_THRESHOLD) -> None:
        self._threshold = long_section_threshold

    def chunk(
        self,
        documents: list[KnowledgeDocument],
        crop_tag: str,
    ) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for doc in documents:
            section_name = doc.metadata.get("section_name", "")
            if len(doc.text) <= self._threshold:
                chunks.append(_make_chunk(doc.text, section_name, doc.metadata, crop_tag))
            else:
                for sub_name, sub_text in _split_at_bold_headers(doc.text, section_name):
                    if sub_text.strip():
                        chunks.append(_make_chunk(sub_text, sub_name, doc.metadata, crop_tag))
        return chunks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(
    text: str,
    section_name: str,
    doc_meta: dict,
    crop_tag: str,
) -> KnowledgeChunk:
    return KnowledgeChunk(
        text_content=text.strip(),
        metadata={
            "crop_tag": crop_tag,
            "section_name": section_name,
            "page_number": 0,
            "crop_name": doc_meta.get("crop_name", ""),
            "scientific_name": doc_meta.get("scientific_name", ""),
            "family": doc_meta.get("family", ""),
        },
    )


def _split_at_bold_headers(text: str, parent_section: str) -> list[tuple[str, str]]:
    """Split *text* at standalone ``**Heading**`` lines without breaking tables.

    A line is treated as a sub-section header when it:
    * starts and ends with ``**``
    * is not indented
    * does not appear inside a Markdown table block

    Table detection: once we see a line starting with ``|`` we consider
    ourselves "inside" a table; we exit when a non-``|`` line follows.
    """
    parts: list[tuple[str, str]] = []
    current_name: str = parent_section
    current_lines: list[str] = []
    in_table = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("|"):
            in_table = True
            current_lines.append(line)
            continue

        if in_table:
            in_table = False

        is_bold_header = (
            stripped.startswith("**")
            and stripped.endswith("**")
            and len(stripped) > 4
            and stripped.count("**") == 2
        )

        if is_bold_header:
            saved = "\n".join(current_lines).strip()
            if saved:
                parts.append((current_name, saved))
            current_name = stripped.strip("*").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        saved = "\n".join(current_lines).strip()
        if saved:
            parts.append((current_name, saved))

    return parts if parts else [(parent_section, text)]
