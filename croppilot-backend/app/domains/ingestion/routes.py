from fastapi import APIRouter, Depends, status

from app.domains.ingestion.dependencies import get_ingestion_service
from app.domains.ingestion.schemas import IngestRequest, IngestResponse
from app.domains.ingestion.service import IngestionService

router = APIRouter()


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestResponse,
    summary="Ingest a knowledge source",
)
async def ingest(
    body: IngestRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    result = service.ingest(body.source_uri, body.crop_name)
    return IngestResponse(
        source_id=result.source_id,
        chunk_count=result.chunk_count,
        status=result.status,
    )
