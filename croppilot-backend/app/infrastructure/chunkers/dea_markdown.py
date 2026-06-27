"""Shared Markdown helpers for DEA gov.lk chunkers."""

from __future__ import annotations

from typing import Literal

BlockKind = Literal["prose", "table"]


def partition_prose_and_tables(text: str) -> list[tuple[BlockKind, str]]:
    """Split *text* into alternating prose and Markdown table blocks.

    Table detection matches ``DeaGovLkChunker``: contiguous lines whose
    stripped form starts with ``|`` form one table block.
    """
    if not text.strip():
        return []

    blocks: list[tuple[BlockKind, str]] = []
    current_kind: BlockKind = "prose"
    current_lines: list[str] = []
    in_table = False

    def flush() -> None:
        nonlocal current_lines
        if not current_lines:
            return
        block = "\n".join(current_lines).strip()
        if block:
            blocks.append((current_kind, block))
        current_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("|"):
            if not in_table:
                flush()
                current_kind = "table"
                in_table = True
            current_lines.append(line)
            continue

        if in_table:
            in_table = False
            flush()
            current_kind = "prose"

        current_lines.append(line)

    flush()
    return blocks if blocks else [("prose", text.strip())]
