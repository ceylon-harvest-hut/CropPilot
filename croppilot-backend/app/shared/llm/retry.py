from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from app.shared.llm.client import LlmClient

logger = logging.getLogger(__name__)

T = TypeVar("T")


def invoke_with_retry(
    fn: Callable[[], T],
    client: LlmClient,
    *,
    max_retries: int,
    default_backoff: float,
    on_retry: Callable[[int, int, float, str], None] | None = None,
) -> T:
    """Call *fn*, retrying when the client's error interpretation says retryable."""
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            info = client.interpret_api_error(exc)
            if not info.retryable or attempt >= max_retries:
                raise
            delay = info.retry_after_seconds if info.retry_after_seconds is not None else default_backoff
            message = info.reason or info.code or str(exc)
            if on_retry is not None:
                on_retry(attempt + 1, max_retries, delay, message)
            else:
                logger.warning(
                    "LLM call failed (attempt %s/%s): %s — retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    message,
                    delay,
                )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
