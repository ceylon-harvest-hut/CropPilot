from __future__ import annotations

import ast
import re

from app.shared.llm.errors import LlmApiErrorInfo

_RETRY_IN_MESSAGE_RE = re.compile(r"Please retry in (\d+(?:\.\d+)?)s", re.IGNORECASE)
_RETRY_DELAY_RE = re.compile(r"'retryDelay':\s*'(\d+(?:\.\d+)?)s'")
_PER_DAY_QUOTA_RE = re.compile(r"PerDay|per_day|_per_day_", re.IGNORECASE)


def interpret_gemini_api_error(exc: BaseException) -> LlmApiErrorInfo:
    message = str(exc)
    upper = message.upper()

    if "RESOURCE_EXHAUSTED" not in upper and "429" not in message:
        return LlmApiErrorInfo(retryable=False, reason=message)

    retry_after = _parse_retry_after_seconds(message)
    is_daily_quota = _is_daily_quota_exhausted(message)

    if is_daily_quota:
        return LlmApiErrorInfo(
            retryable=False,
            retry_after_seconds=retry_after,
            code="RESOURCE_EXHAUSTED",
            reason="Daily quota exhausted",
        )

    return LlmApiErrorInfo(
        retryable=True,
        retry_after_seconds=retry_after,
        code="RESOURCE_EXHAUSTED",
        reason="Rate limit exceeded",
    )


def _parse_retry_after_seconds(message: str) -> float | None:
    match = _RETRY_IN_MESSAGE_RE.search(message)
    if match:
        return float(match.group(1))

    delay_match = _RETRY_DELAY_RE.search(message)
    if delay_match:
        return float(delay_match.group(1))

    parsed = _retry_delay_from_embedded_dict(message)
    if parsed is not None:
        return parsed

    return None


def _retry_delay_from_embedded_dict(message: str) -> float | None:
    dict_start = message.find("{")
    if dict_start < 0:
        return None
    fragment = message[dict_start:]
    try:
        payload = ast.literal_eval(fragment)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    error = payload.get("error")
    if not isinstance(error, dict):
        return None

    for detail in error.get("details", []):
        if not isinstance(detail, dict):
            continue
        if detail.get("@type") != "type.googleapis.com/google.rpc.RetryInfo":
            continue
        retry_delay = detail.get("retryDelay", "")
        if isinstance(retry_delay, str) and retry_delay.endswith("s"):
            try:
                return float(retry_delay[:-1])
            except ValueError:
                return None
    return None


def _is_daily_quota_exhausted(message: str) -> bool:
    if _PER_DAY_QUOTA_RE.search(message):
        return True

    dict_start = message.find("{")
    if dict_start < 0:
        return False
    try:
        payload = ast.literal_eval(message[dict_start:])
    except (SyntaxError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False

    error = payload.get("error")
    if not isinstance(error, dict):
        return False

    for detail in error.get("details", []):
        if not isinstance(detail, dict):
            continue
        for violation in detail.get("violations", []):
            if not isinstance(violation, dict):
                continue
            quota_id = str(violation.get("quotaId", ""))
            quota_metric = str(violation.get("quotaMetric", ""))
            if "PerDay" in quota_id or "per_day" in quota_metric.lower():
                return True
    return False
