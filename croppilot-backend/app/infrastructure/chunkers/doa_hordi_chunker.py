"""Chunker alias for DOA HORDI loader output."""

from __future__ import annotations

from app.infrastructure.chunkers.dea_gov_lk_chunker import DeaGovLkChunker


class DoaHordiChunker(DeaGovLkChunker):
    """Produce KnowledgeChunks from DoaHordiLoader output."""

    name = "doa_hordi"
