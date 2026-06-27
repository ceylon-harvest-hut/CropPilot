from functools import lru_cache

from fastapi import Depends

from app.domains.inference.service import InferenceService
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.factories import build_inference_service


@lru_cache(maxsize=1)
def _get_cached_inference_service(
    embedding_backend: str,
    fastembed_cache_dir: str,
    hf_hub_offline: bool,
    llm_backend: str,
    retrieval_top_k: int,
) -> InferenceService:
    """Build and cache the InferenceService exactly once per unique config combo.

    The embedder loads a ~2 GB ONNX model — we must not reconstruct it on
    every request.  Caching on the config fields (not the Settings object
    itself, which is not hashable by default) ensures the cache invalidates
    correctly if settings change between test runs.
    """
    settings = get_settings()
    return build_inference_service(settings)


def get_inference_service(
    settings: Settings = Depends(get_settings),
) -> InferenceService:
    return _get_cached_inference_service(
        embedding_backend=settings.embedding_backend,
        fastembed_cache_dir=settings.fastembed_cache_dir,
        hf_hub_offline=settings.hf_hub_offline,
        llm_backend=settings.llm_backend,
        retrieval_top_k=settings.retrieval_top_k,
    )
