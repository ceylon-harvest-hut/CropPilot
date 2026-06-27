"""Text conversion helpers for DOA gov.lk Elementor crop pages."""

from __future__ import annotations

from bs4 import NavigableString, Tag

from app.infrastructure.loaders.dea_gov_lk_loader import _table_to_markdown


def table_to_markdown(table: Tag) -> str:
    return _table_to_markdown(table)


def html_fragment_to_text(root: Tag) -> str:
    """Convert an Elementor widget container to plain/Markdown text."""
    parts: list[str] = []
    for child in root.children:
        if isinstance(child, NavigableString):
            text = child.strip()
            if text:
                parts.append(text)
        elif isinstance(child, Tag):
            text = _tag_to_text(child)
            if text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def toggle_item_to_text(title: str, content: Tag) -> str:
    body = html_fragment_to_text(content)
    title = title.strip()
    if not body:
        return f"**{title}**" if title else ""
    if title:
        return f"**{title}**\n\n{body}"
    return body


def icon_list_to_text(widget: Tag) -> str:
    items: list[str] = []
    for li in widget.select(".elementor-icon-list-item"):
        text = li.get_text(separator=" ", strip=True)
        if text:
            items.append(f"- {text}")
    return "\n".join(items)


def _tag_to_text(tag: Tag) -> str:
    name = tag.name
    if name in ("script", "style", "noscript", "img"):
        return ""
    if name == "table":
        return table_to_markdown(tag)
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        text = tag.get_text(strip=True)
        return f"**{text}**" if text else ""
    if name == "p":
        return _inline_to_text(tag)
    if name in ("ul", "ol"):
        return _list_to_text(tag)
    if name == "br":
        return "\n"
    if name in ("div", "span", "section"):
        return html_fragment_to_text(tag)
    return tag.get_text(separator=" ", strip=True)


def _inline_to_text(tag: Tag) -> str:
    parts: list[str] = []
    for child in tag.children:
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
            elif cn == "table":
                parts.append("\n" + table_to_markdown(child) + "\n")
            elif cn in ("ul", "ol"):
                parts.append("\n" + _list_to_text(child))
            else:
                parts.append(child.get_text(separator=" ", strip=True))
    raw_text = "".join(parts)
    lines = [" ".join(line.split()) for line in raw_text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _list_to_text(tag: Tag) -> str:
    items: list[str] = []
    for li in tag.find_all("li", recursive=False):
        text = li.get_text(separator=" ", strip=True)
        if text:
            items.append(f"- {text}")
    return "\n".join(items)
