"""Chunker alias for Sinhala DEA loader output.

Uses the same logic as ``DeaGovLkChunker`` — section documents from
``DeaGovLkSiLoader`` share the same shape (section text with ``**sub-headers**``
and Markdown tables).
"""

from __future__ import annotations

from app.infrastructure.chunkers.dea_gov_lk_chunker import DeaGovLkChunker


class DeaGovLkSiChunker(DeaGovLkChunker):
    """Produce KnowledgeChunks from DeaGovLkSiLoader output."""

    name = "dea_gov_lk_si"
