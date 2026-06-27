"""Root-level pytest fixtures shared across all test suites.

The FastAPI app lifespan warms up the InferenceService (loads the ONNX
embedding model) at startup.  This is the correct production behaviour, but
it requires a bootstrapped model cache.  Fast unit / route tests must not
trigger that download, so we patch the cached builder here.

Slow integration tests (marked ``@pytest.mark.slow``) exercise the real
stack and must NOT use this override.  They rely on a real model cache
being available in the test environment.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.domains.inference.service import InferenceService


@pytest.fixture(autouse=True)
def _mock_inference_startup(request):
    """Prevent the lifespan warmup from loading the real ONNX model.

    Skipped automatically for tests marked ``slow`` (they have a real cache).
    """
    if request.node.get_closest_marker("slow"):
        yield
        return

    mock_service = MagicMock(spec=InferenceService)
    with patch(
        "app.domains.inference.dependencies._get_cached_inference_service",
        return_value=mock_service,
    ):
        yield
