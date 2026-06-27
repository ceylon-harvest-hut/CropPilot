"""Loader for Sinhala DEA gov.lk crop pages (dea.gov.lk/language/si/…).

Sinhala pages use the same WordPress template as English but different heading
levels:

  - Crop name  : ``h2.has-text-align-center`` (English uses h3)
  - Sci. name  : ``h4/h5.has-text-align-center`` with ``කුලය:`` family label
  - Sections   : ``h3.wp-block-heading`` WITHOUT ``has-text-align-center``
                 (English uses h4; h4 here are sub-sections kept in body)
  - Tables     : ``figure.wp-block-table > table`` (unchanged)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from app.domains.ingestion.content import LoaderOptions, RawContent
from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.loaders.dea_gov_lk_loader import _nodes_to_text
from app.infrastructure.loaders.persist import maybe_persist_output

_FAMILY_PATTERN = re.compile(r"(?:[Ff]amily|කුලය)\s*[:\-]\s*(.+)")


class DeaGovLkSiLoader(DocumentLoader):
    """Parse a Sinhala DEA gov.lk HTML crop page into per-section KnowledgeDocuments."""

    name = "dea_gov_lk_si"

    def supports(self, raw: RawContent) -> bool:
        ext = Path(raw.source_uri).suffix.lower() if raw.source_uri else ""
        return "text/html" in raw.media_type or ext in {".html", ".htm"}

    def load(
        self,
        raw: RawContent,
        options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]:
        if raw.data:
            html = raw.data.decode(raw.charset, errors="replace")
        elif raw.local_path is not None:
            html = raw.local_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"No content available for: {raw.source_uri}")

        soup = BeautifulSoup(html, "html.parser")
        entry = soup.select_one("div.entry-content")
        if entry is None:
            raise ValueError(f"No entry-content div found in: {raw.source_uri}")

        crop_name = _extract_crop_name(entry)
        scientific_name, family = _extract_scientific(entry)

        base_meta: dict[str, Any] = {
            "source_uri": raw.source_uri,
            "source_type": raw.source_type,
            "loader": self.name,
            "media_type": raw.media_type,
            "final_url": raw.resolved_uri,
            "crop_name": crop_name,
            "scientific_name": scientific_name,
            "family": family,
        }

        docs: list[KnowledgeDocument] = []
        for section_name, nodes in _split_sections(entry):
            text = _nodes_to_text(nodes)
            if not text.strip():
                continue
            docs.append(
                KnowledgeDocument(
                    text=text.strip(),
                    metadata={**base_meta, "section_name": section_name},
                )
            )

        if not docs:
            raise ValueError(f"No sections extracted from: {raw.source_uri}")

        if options:
            maybe_persist_output(docs, options)

        return docs


def _extract_crop_name(entry: Tag) -> str:
    for tag_name in ("h2", "h3"):
        tag = entry.find(tag_name, class_="has-text-align-center")
        if tag:
            return tag.get_text(strip=True)
    return ""


def _extract_scientific(entry: Tag) -> tuple[str, str]:
    for tag_name in ("h4", "h5"):
        tag = entry.find(tag_name, class_="has-text-align-center")
        if tag is None:
            continue
        em = tag.find("em")
        scientific_name = em.get_text(strip=True) if em else ""
        full_text = tag.get_text(separator=" ", strip=True)
        family = ""
        match = _FAMILY_PATTERN.search(full_text)
        if match:
            family = match.group(1).strip()
        return scientific_name, family
    return "", ""


def _is_section_header(tag: Any) -> bool:
    """True for h3 with wp-block-heading but NOT has-text-align-center."""
    if not isinstance(tag, Tag):
        return False
    if tag.name != "h3":
        return False
    classes = set(tag.get("class") or [])
    return "wp-block-heading" in classes and "has-text-align-center" not in classes


def _split_sections(entry: Tag) -> list[tuple[str, list[Any]]]:
    """Walk entry-content children and group nodes by h3 section header."""
    sections: list[tuple[str, list[Any]]] = []
    overview_nodes: list[Any] = []
    current_section: str | None = None
    current_nodes: list[Any] = []

    for child in entry.children:
        if isinstance(child, NavigableString):
            if child.strip():
                (current_nodes if current_section is not None else overview_nodes).append(child)
            continue

        if _is_section_header(child):
            if current_section is not None:
                sections.append((current_section, current_nodes))
            elif overview_nodes:
                sections.append(("Overview", overview_nodes))
            current_section = child.get_text(strip=True)
            current_nodes = []
        else:
            (current_nodes if current_section is not None else overview_nodes).append(child)

    if current_section is not None and current_nodes:
        sections.append((current_section, current_nodes))
    elif overview_nodes and not sections:
        sections.append(("Overview", overview_nodes))

    return sections
