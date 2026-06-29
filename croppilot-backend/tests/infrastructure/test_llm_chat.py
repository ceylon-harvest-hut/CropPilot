import sys
from unittest.mock import MagicMock


def _make_mock_module(class_name: str) -> MagicMock:
    """Return a module mock that exposes a MagicMock under *class_name*."""
    module = MagicMock()
    setattr(module, class_name, MagicMock(return_value=MagicMock()))
    return module


def test_gemini_generate_returns_string() -> None:
    fake_module = _make_mock_module("ChatGoogleGenerativeAI")

    with MagicMock() as mock_chain_result:
        mock_chain_result.invoke.return_value = "Pepper is grown in tropical regions."

        fake_module.ChatGoogleGenerativeAI.return_value = MagicMock()

        original = sys.modules.get("langchain_google_genai")
        sys.modules["langchain_google_genai"] = fake_module
        try:
            from app.infrastructure.llm.chat import GeminiLlmService

            service = GeminiLlmService(
                model_name="models/gemini-2.5-flash",
                api_key="test-key",
            )
            service._chains = {"context_only": mock_chain_result}

            result = service.generate("Where is pepper grown?", "Pepper grows in tropics.")
        finally:
            if original is None:
                sys.modules.pop("langchain_google_genai", None)
            else:
                sys.modules["langchain_google_genai"] = original

    assert result == "Pepper is grown in tropical regions."
    mock_chain_result.invoke.assert_called_once_with(
        {"question": "Where is pepper grown?", "context": "Pepper grows in tropics."}
    )


def test_gemini_generate_uses_named_template() -> None:
    fake_module = _make_mock_module("ChatGoogleGenerativeAI")

    context_chain = MagicMock()
    context_chain.invoke.return_value = "Strict answer."
    hybrid_chain = MagicMock()
    hybrid_chain.invoke.return_value = "Hybrid answer."

    fake_module.ChatGoogleGenerativeAI.return_value = MagicMock()

    original = sys.modules.get("langchain_google_genai")
    sys.modules["langchain_google_genai"] = fake_module
    try:
        from app.infrastructure.llm.chat import GeminiLlmService

        service = GeminiLlmService(
            model_name="models/gemini-2.5-flash",
            api_key="test-key",
        )
        service._chains = {
            "context_only": context_chain,
            "hybrid": hybrid_chain,
        }

        result = service.generate("Q?", "ctx", template="hybrid")
    finally:
        if original is None:
            sys.modules.pop("langchain_google_genai", None)
        else:
            sys.modules["langchain_google_genai"] = original

    assert result == "Hybrid answer."
    hybrid_chain.invoke.assert_called_once()
    context_chain.invoke.assert_not_called()


def test_ollama_generate_returns_string(monkeypatch) -> None:
    fake_module = _make_mock_module("ChatOllama")
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake_module)

    from app.infrastructure.llm.chat import OllamaLlmService

    service = OllamaLlmService(model_name="llama3")

    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Pepper needs high humidity."
    service._chains = {"context_only": mock_chain}

    result = service.generate("What does pepper need?", "Pepper needs humidity.")

    assert isinstance(result, str)
    assert result == "Pepper needs high humidity."


def test_openai_generate_returns_string(monkeypatch) -> None:
    fake_module = _make_mock_module("ChatOpenAI")
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)

    from app.infrastructure.llm.chat import OpenAILlmService

    service = OpenAILlmService(model_name="gpt-4o-mini")

    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Pepper has many varieties."
    service._chains = {"context_only": mock_chain}

    result = service.generate("What varieties does pepper have?", "Pepper has many.")

    assert isinstance(result, str)
    assert result == "Pepper has many varieties."


def test_gemini_interpret_api_error_delegates_to_parser() -> None:
    from app.infrastructure.llm.chat import GeminiLlmClient

    client = GeminiLlmClient.__new__(GeminiLlmClient)
    info = client.interpret_api_error(RuntimeError("429 RESOURCE_EXHAUSTED Please retry in 5s."))
    assert info.code == "RESOURCE_EXHAUSTED"
    assert info.retryable is True
    assert info.retry_after_seconds == 5.0
