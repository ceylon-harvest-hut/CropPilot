from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.agent.gemini_agent_client import GeminiAgentClient
from app.infrastructure.agent.openai_agent_client import OpenAIAgentClient
from app.infrastructure.factories import build_agent_client


@pytest.fixture
def base_settings() -> Settings:
    return Settings(
        llm_backend="gemini",
        google_api_key="gemini-key",
        openai_api_key="openai-key",
        neo4j_password="secret",
    )


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
@patch("app.infrastructure.agent.tools.spacing.build_spacing_langchain_tool")
@patch("app.infrastructure.factories.build_neo4j_driver")
def test_build_agent_client_returns_gemini_client(
    mock_build_driver: MagicMock,
    mock_build_tool: MagicMock,
    mock_chat_cls: MagicMock,
    base_settings: Settings,
) -> None:
    mock_build_tool.return_value = MagicMock(name="spacing_tool")

    client = build_agent_client(base_settings)

    assert isinstance(client, GeminiAgentClient)
    mock_chat_cls.assert_called_once()


@patch("langchain_openai.ChatOpenAI")
@patch("app.infrastructure.agent.tools.spacing.build_spacing_langchain_tool")
@patch("app.infrastructure.factories.build_neo4j_driver")
def test_build_agent_client_returns_openai_client(
    mock_build_driver: MagicMock,
    mock_build_tool: MagicMock,
    mock_chat_cls: MagicMock,
    base_settings: Settings,
) -> None:
    mock_build_tool.return_value = MagicMock(name="spacing_tool")
    settings = base_settings.model_copy(update={"llm_backend": "openai"})

    client = build_agent_client(settings)

    assert isinstance(client, OpenAIAgentClient)
    mock_chat_cls.assert_called_once()


def test_build_agent_client_rejects_ollama(base_settings: Settings) -> None:
    settings = base_settings.model_copy(update={"llm_backend": "ollama"})

    with pytest.raises(ValueError, match="gemini or openai only"):
        build_agent_client(settings)


def test_build_agent_client_requires_openai_api_key(base_settings: Settings) -> None:
    settings = base_settings.model_copy(
        update={"llm_backend": "openai", "openai_api_key": None}
    )

    with pytest.raises(ValueError, match="OpenAI API key required"):
        build_agent_client(settings)
