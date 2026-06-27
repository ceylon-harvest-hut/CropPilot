from app.infrastructure.llm.prompt_catalog import (
    DEFAULT_ASK_TEMPLATE,
    get_prompt_template,
    list_prompt_template_options,
    list_template_names,
    resolve_template_name,
)


def test_list_template_names() -> None:
    names = list_template_names()
    assert "context_only" in names
    assert "hybrid" in names


def test_list_prompt_template_options_has_labels() -> None:
    options = list_prompt_template_options()
    assert len(options) >= 2
    assert all(option.name and option.label and option.description for option in options)


def test_get_prompt_template_known() -> None:
    text = get_prompt_template("hybrid")
    assert "general knowledge" in text.lower()


def test_get_prompt_template_unknown_raises() -> None:
    try:
        get_prompt_template("unknown")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unknown" in str(exc).lower()


def test_resolve_template_name_uses_default() -> None:
    assert resolve_template_name(None) == DEFAULT_ASK_TEMPLATE


def test_resolve_template_name_explicit() -> None:
    assert resolve_template_name("hybrid") == "hybrid"
