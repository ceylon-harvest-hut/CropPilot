from __future__ import annotations

from app.infrastructure.llm.gemini_api_errors import interpret_gemini_api_error

DAILY_QUOTA_ERROR = (
    "Error calling model 'models/gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. "
    "{'error': {'code': 429, 'message': 'You exceeded your current quota. "
    "Please retry in 45.094267346s.', 'status': 'RESOURCE_EXHAUSTED', "
    "'details': [{'@type': 'type.googleapis.com/google.rpc.QuotaFailure', "
    "'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', "
    "'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaValue': '20'}]}, "
    "{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '45s'}]}}"
)

RPM_ERROR = (
    "Error calling model 'models/gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. "
    "{'error': {'code': 429, 'message': 'Rate limit. Please retry in 12.5s.', "
    "'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', "
    "'retryDelay': '12s'}]}}"
)


def test_daily_quota_is_not_retryable() -> None:
    info = interpret_gemini_api_error(RuntimeError(DAILY_QUOTA_ERROR))
    assert info.retryable is False
    assert info.code == "RESOURCE_EXHAUSTED"
    assert "Daily quota" in info.reason
    assert info.retry_after_seconds == 45.094267346


def test_rpm_limit_is_retryable_with_delay() -> None:
    info = interpret_gemini_api_error(RuntimeError(RPM_ERROR))
    assert info.retryable is True
    assert info.code == "RESOURCE_EXHAUSTED"
    assert info.retry_after_seconds == 12.5


def test_unknown_error_is_not_retryable() -> None:
    info = interpret_gemini_api_error(RuntimeError("connection reset"))
    assert info.retryable is False
