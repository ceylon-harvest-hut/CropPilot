from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.shared.llm.errors import LlmApiErrorInfo
from app.shared.llm.retry import invoke_with_retry


def test_invoke_with_retry_succeeds_on_second_attempt() -> None:
    client = MagicMock()
    client.interpret_api_error.return_value = LlmApiErrorInfo(
        retryable=True,
        retry_after_seconds=0.0,
        code="RESOURCE_EXHAUSTED",
    )
    calls = {"count": 0}

    def fn():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("rate limited")
        return "ok"

    result = invoke_with_retry(fn, client, max_retries=2, default_backoff=0.0)
    assert result == "ok"
    assert calls["count"] == 2


def test_invoke_with_retry_raises_when_not_retryable() -> None:
    client = MagicMock()
    client.interpret_api_error.return_value = LlmApiErrorInfo(retryable=False, reason="bad request")

    def failing() -> str:
        raise RuntimeError("bad request")

    with pytest.raises(RuntimeError, match="bad request"):
        invoke_with_retry(failing, client, max_retries=3, default_backoff=0.0)


def test_invoke_with_retry_stops_after_max_retries() -> None:
    client = MagicMock()
    client.interpret_api_error.return_value = LlmApiErrorInfo(
        retryable=True,
        retry_after_seconds=0.0,
    )
    calls = {"count": 0}

    def fn():
        calls["count"] += 1
        raise RuntimeError("still limited")

    with pytest.raises(RuntimeError, match="still limited"):
        invoke_with_retry(fn, client, max_retries=2, default_backoff=0.0)

    assert calls["count"] == 3
