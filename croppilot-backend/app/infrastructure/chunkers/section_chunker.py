from __future__ import annotations

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument

INTRODUCTION_SECTION = "Introduction"
MAX_SECTION_HEADER_LENGTH = 100


class SectionChunker(BaseChunker):
    """Split crop documents on section headers into KnowledgeChunk objects.

    Iterates over all documents, splitting each by section header. Page number
    is inherited from the document's ``page`` metadata key when available.
    """

    def chunk(
        self,
        documents: list[KnowledgeDocument],
        crop_tag: str,
    ) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for doc in documents:
            page = int(doc.metadata.get("page", 0))
            text = doc.text.strip()
            for section_name, section_text in self._split_into_sections(text.splitlines()):
                if not section_text.strip():
                    continue
                chunks.append(
                    KnowledgeChunk(
                        text_content=section_text.strip(),
                        metadata={
                            "crop_tag": crop_tag,
                            "section_name": section_name,
                            "page_number": page,
                        },
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
