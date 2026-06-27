"""Registry of Ask prompt templates."""

from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.llm.prompts import CROP_HYBRID_PROMPT, CROP_RAG_PROMPT

DEFAULT_ASK_TEMPLATE = "context_only"


@dataclass(frozen=True)
class PromptTemplateOption:
    name: str
    label: str
    description: str


_TEMPLATE_OPTIONS: tuple[PromptTemplateOption, ...] = (
    PromptTemplateOption(
        name="context_only",
        label="Source documents only",
        description="Answer strictly from retrieved source documents.",
    ),
    PromptTemplateOption(
        name="hybrid",
        label="Documents + general knowledge",
        description=(
            "Combine source documents with general agronomic knowledge when context is thin."
        ),
    ),
)

_PROMPT_TEMPLATES: dict[str, str] = {
    "context_only": CROP_RAG_PROMPT,
    "hybrid": CROP_HYBRID_PROMPT,
}


def list_prompt_template_options() -> list[PromptTemplateOption]:
    return list(_TEMPLATE_OPTIONS)


def list_template_names() -> list[str]:
    return list(_PROMPT_TEMPLATES.keys())


def get_prompt_template(name: str) -> str:
    try:
        return _PROMPT_TEMPLATES[name]
    except KeyError:
        known = ", ".join(sorted(_PROMPT_TEMPLATES))
        raise ValueError(f"Unknown ask template: {name!r}. Available: {known}")


def resolve_template_name(name: str | None, default: str = DEFAULT_ASK_TEMPLATE) -> str:
    resolved = name or default
    get_prompt_template(resolved)
    return resolved
