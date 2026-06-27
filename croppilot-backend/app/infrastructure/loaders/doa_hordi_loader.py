"""Loader for DOA gov.lk HORDI crop pages (Elementor / Agritek theme).

HORDI crop guides on doa.gov.lk are built with Elementor widgets inside
``article .entry-content``.  The loader walks widgets in document order and
emits one ``KnowledgeDocument`` per section (toggle items become separate docs).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.domains.ingestion.content import LoaderOptions, RawContent
from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.loaders.doa_elementor import (
    html_fragment_to_text,
    icon_list_to_text,
    toggle_item_to_text,
)
from app.infrastructure.loaders.persist import maybe_persist_output

_SKIP_WIDGET_TYPES = frozenset(
    {
        "image.default",
        "divider.default",
    }
)


class DoaHordiLoader(DocumentLoader):
    """Parse a DOA HORDI Elementor HTML crop page into per-section KnowledgeDocuments."""

    name = "doa_hordi"

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
        root = _find_elementor_root(soup)
        if root is None:
            raise ValueError(f"No Elementor page root found in: {raw.source_uri}")

        crop_name, scientific_name = _extract_crop_metadata(root)
        base_meta: dict[str, Any] = {
            "source_uri": raw.source_uri,
            "source_type": raw.source_type,
            "loader": self.name,
            "media_type": raw.media_type,
            "final_url": raw.resolved_uri,
            "crop_name": crop_name,
            "scientific_name": scientific_name,
            "family": "",
        }

        docs = _widgets_to_documents(root, base_meta, crop_name_found=bool(crop_name))
        if not docs:
            raise ValueError(f"No sections extracted from: {raw.source_uri}")

        if options:
            maybe_persist_output(docs, options)

        return docs


def _find_elementor_root(soup: BeautifulSoup) -> Tag | None:
    root = soup.select_one('article .entry-content div[data-elementor-type="wp-page"]')
    if root is not None:
        return root
    return soup.select_one("article .entry-content div.elementor")


def _extract_crop_metadata(root: Tag) -> tuple[str, str]:
    crop_name = ""
    scientific_name = ""
    for widget in root.select('[data-widget_type="heading.default"]'):
        h2 = widget.select_one("h2.elementor-heading-title")
        if h2 is None:
            continue
        if h2.find("em"):
            if not scientific_name:
                scientific_name = h2.get_text(separator=" ", strip=True)
        elif not crop_name:
            crop_name = h2.get_text(strip=True)
        if crop_name and scientific_name:
            break
    return crop_name, scientific_name


def _heading_text(widget: Tag) -> str:
    for tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        heading = widget.find(tag_name, class_="elementor-heading-title")
        if heading:
            return heading.get_text(strip=True)
    return ""


def _is_metadata_heading(widget: Tag, crop_name: str, scientific_name: str) -> bool:
    text = _heading_text(widget)
    if not text:
        return True
    if crop_name and text == crop_name:
        return True
    if scientific_name and text == scientific_name:
        return True
    return bool(widget.select_one("h2.elementor-heading-title em"))


def _widgets_to_documents(
    root: Tag,
    base_meta: dict[str, Any],
    *,
    crop_name_found: bool,
) -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    current_section = ""
    current_parts: list[str] = []
    crop_name = base_meta.get("crop_name", "")
    scientific_name = base_meta.get("scientific_name", "")
    started = not crop_name_found

    def flush_section() -> None:
        nonlocal current_parts
        if not current_section:
            current_parts = []
            return
        text = "\n\n".join(part for part in current_parts if part.strip()).strip()
        if text:
            docs.append(
                KnowledgeDocument(
                    text=text,
                    metadata={**base_meta, "section_name": current_section},
                )
            )
        current_parts = []

    for widget in root.select("[data-widget_type]"):
        widget_type = widget.get("data-widget_type", "")

        if widget_type in _SKIP_WIDGET_TYPES:
            continue

        if widget_type == "heading.default":
            heading_text = _heading_text(widget)
            if not heading_text:
                continue
            if not started:
                if _is_metadata_heading(widget, crop_name, scientific_name):
                    if heading_text == crop_name:
                        started = True
                    continue
                started = True
            flush_section()
            current_section = heading_text
            continue

        if not started:
            continue

        if widget_type == "text-editor.default":
            container = widget.select_one(".elementor-widget-container")
            if container is None:
                continue
            text = html_fragment_to_text(container)
            if text:
                if not current_section:
                    current_section = "Overview"
                current_parts.append(text)
            continue

        if widget_type == "icon-list.default":
            text = icon_list_to_text(widget)
            if text:
                if not current_section:
                    current_section = "Overview"
                current_parts.append(text)
            continue

        if widget_type == "toggle.default":
            flush_section()
            parent_section = current_section or "Overview"
            for item in widget.select(".elementor-toggle-item"):
                title_el = item.select_one(".elementor-toggle-title")
                content_el = item.select_one(".elementor-tab-content")
                if title_el is None or content_el is None:
                    continue
                title = title_el.get_text(separator=" ", strip=True)
                text = toggle_item_to_text(title, content_el)
                if not text.strip():
                    continue
                section_name = f"{parent_section} / {title}" if parent_section else title
                docs.append(
                    KnowledgeDocument(
                        text=text.strip(),
                        metadata={**base_meta, "section_name": section_name},
                    )
                )
            continue

    flush_section()
    return docs
