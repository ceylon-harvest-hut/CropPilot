from __future__ import annotations

from typing import Protocol

from app.domains.ingestion.data import ChunkMetadata, KnowledgeChunk

INTRODUCTION_SECTION = "Introduction"
MAX_SECTION_HEADER_LENGTH = 100


class ChunkingStrategy(Protocol):
    def split(self, text: str, crop_tag: str) -> list[KnowledgeChunk]: ...


class BaseChunker:
    """Template method: preprocess -> strategy.split -> postprocess."""

    def __init__(self, strategy: ChunkingStrategy) -> None:
        self._strategy = strategy

    def chunk(self, text: str, crop_tag: str) -> list[KnowledgeChunk]:
        text = self.preprocess(text)
        chunks = self._strategy.split(text, crop_tag)
        return self.postprocess(chunks)

    def preprocess(self, text: str) -> str:
        return text.strip()

    def postprocess(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
        return [chunk for chunk in chunks if chunk.text_content.strip()]


class SectionChunkingStrategy:
    """Split crop documents on section headers into KnowledgeChunk objects."""

    def split(self, text: str, crop_tag: str) -> list[KnowledgeChunk]:
        lines = text.splitlines()
        sections = self._split_into_sections(lines)

        chunks: list[KnowledgeChunk] = []
        for section_name, section_text in sections:
            if not section_text.strip():
                continue

            chunks.append(
                KnowledgeChunk(
                    text_content=section_text.strip(),
                    metadata=ChunkMetadata(
                        section_name=section_name,
                        page_number=0,
                        crop_tag=crop_tag,
                    ),
                )
            )

        return chunks

    def _split_into_sections(self, lines: list[str]) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        preamble_lines: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            next_line = lines[index + 1] if index + 1 < len(lines) else None

            if self._is_section_header(line, next_line):
                if preamble_lines and not sections:
                    sections.append(
                        (INTRODUCTION_SECTION, "\n".join(preamble_lines).strip())
                    )
                    preamble_lines = []

                section_name = line.strip()
                index += 2 if next_line is not None and not next_line.strip() else 1

                content_lines: list[str] = []
                while index < len(lines):
                    candidate = lines[index]
                    candidate_next = lines[index + 1] if index + 1 < len(lines) else None
                    if self._is_section_header(candidate, candidate_next):
                        break
                    content_lines.append(candidate)
                    index += 1

                sections.append((section_name, "\n".join(content_lines).strip()))
            else:
                preamble_lines.append(line)
                index += 1

        if preamble_lines and not sections:
            sections.append((INTRODUCTION_SECTION, "\n".join(preamble_lines).strip()))

        return sections

    def _is_section_header(self, line: str, next_line: str | None) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if line.startswith("    "):
            return False
        if len(stripped) > MAX_SECTION_HEADER_LENGTH:
            return False
        if stripped.endswith("."):
            return False
        if next_line is not None and next_line.strip():
            return False
        return True
