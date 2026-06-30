from functools import lru_cache

from fastapi import Depends, HTTPException, status

from app.domains.agent.service import AgentService
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.factories import build_agent_service


@lru_cache(maxsize=1)
def _get_cached_agent_service(
    llm_backend: str,
    gemini_model: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
) -> AgentService:
    settings = get_settings()
    return build_agent_service(settings)


def get_agent_service(
    settings: Settings = Depends(get_settings),
) -> AgentService:
    try:
        return _get_cached_agent_service(
            llm_backend=settings.llm_backend,
            gemini_model=settings.gemini_model,
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
