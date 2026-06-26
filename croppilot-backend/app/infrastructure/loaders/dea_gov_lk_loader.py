"""Loader for DEA gov.lk crop pages (dea.gov.lk/{crop}/).

Every crop page shares the same WordPress/Spacious template:
  - Main content is inside ``article > div.entry-content.clearfix``
  - Crop name  : ``h3.has-text-align-center``
  - Sci. name  : ``h4/h5.has-text-align-center`` (contains <em> + "Family: ...")
  - Sections   : ``h4.wp-block-heading`` WITHOUT ``has-text-align-center``
  - Tables     : ``figure.wp-block-table > table``

The loader produces ONE ``KnowledgeDocument`` per section, injecting
``section_name``, ``crop_name``, ``scientific_name`` and ``family`` into
metadata so the downstream chunker can operate on clean, labelled slices.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from app.domains.ingestion.content import LoaderOptions, RawContent
from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.loaders.persist import maybe_persist_output


class DeaGovLkLoader(DocumentLoader):
    """Parse a DEA gov.lk HTML crop page into per-section KnowledgeDocuments."""

    name = "dea_gov_lk"

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_crop_name(entry: Tag) -> str:
    h3 = entry.find("h3", class_="has-text-align-center")
    if h3:
        return h3.get_text(strip=True)
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
        match = re.search(r"[Ff]amily\s*[:\-]\s*(.+)", full_text)
        if match:
            family = match.group(1).strip()
        return scientific_name, family
    return "", ""


def _is_section_header(tag: Any) -> bool:
    """True for h4 with wp-block-heading but NOT has-text-align-center."""
    if not isinstance(tag, Tag):
        return False
    if tag.name != "h4":
        return False
    classes = set(tag.get("class") or [])
    return "wp-block-heading" in classes and "has-text-align-center" not in classes


def _split_sections(entry: Tag) -> list[tuple[str, list[Any]]]:
    """Walk entry-content children and group nodes by section header."""
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


def _nodes_to_text(nodes: list[Any]) -> str:
    parts = []
    for node in nodes:
        if isinstance(node, NavigableString):
            t = node.strip()
            if t:
                parts.append(t)
        elif isinstance(node, Tag):
            text = _tag_to_text(node)
            if text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def _tag_to_text(tag: Tag) -> str:
    name = tag.name
    if name in ("script", "style", "noscript", "img"):
        return ""
    if name in ("h3", "h4", "h5", "h6"):
        text = tag.get_text(strip=True)
        return f"**{text}**" if text else ""
    if name == "p":
        return _p_to_text(tag)
    if name in ("ul", "ol"):
        return _list_to_text(tag)
    if name == "figure":
        classes = set(tag.get("class") or [])
        if "wp-block-table" in classes:
            table = tag.find("table")
            return _table_to_markdown(table) if table else ""
        return ""
    if name == "div":
        return _nodes_to_text(list(tag.children))
    return tag.get_text(separator=" ", strip=True)


def _p_to_text(p: Tag) -> str:
    """Render a <p> to text, preserving **bold** markers and line breaks."""
    parts: list[str] = []
    for child in p.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            cn = child.name
            if cn == "strong":
                text = child.get_text(strip=True)
                parts.append(f"**{text}**" if text else "")
            elif cn == "em":
                text = child.get_text(strip=True)
                parts.append(f"*{text}*" if text else "")
            elif cn == "br":
                parts.append("\n")
            elif cn == "sup":
                parts.append(child.get_text(strip=True))
            elif cn == "a":
                parts.append(child.get_text(strip=True))
            else:
                parts.append(child.get_text(separator=" ", strip=True))
    raw_text = "".join(parts)
    lines = [" ".join(line.split()) for line in raw_text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _list_to_text(tag: Tag) -> str:
    items = []
    for li in tag.find_all("li", recursive=False):
        text = li.get_text(separator=" ", strip=True)
        if text:
            items.append(f"- {text}")
    return "\n".join(items)


def _table_to_markdown(table: Tag) -> str:
    rows = []
    all_rows = table.find_all("tr")
    for i, tr in enumerate(all_rows):
        cells = []
        for cell in tr.find_all(["th", "td"]):
            text = cell.get_text(separator=" ", strip=True).replace("|", "\\|")
            cells.append(text)
        if not cells:
            continue
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)
