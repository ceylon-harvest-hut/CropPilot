from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmApiErrorInfo:
    retryable: bool
    retry_after_seconds: float | None = None
    code: str = ""
    reason: str = ""
