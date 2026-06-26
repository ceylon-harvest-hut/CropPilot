from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.ingestion.dependencies import get_ingestion_service
from app.domains.ingestion.persistence import SourceAlreadyIngestedError
from app.domains.ingestion.schemas import IngestRequest, IngestResponse
from app.domains.ingestion.service import IngestionService
from app.infrastructure.loaders.validation import LoaderValidationError

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
    try:
        result = service.ingest(
            body.source_uri,
            body.crop_name,
            source_type=body.source_type,
            loader=body.loader,
            replace_existing=body.replace_existing,
        )
    except SourceAlreadyIngestedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Source already ingested. Set replace_existing=true to replace vectors.",
                "source_id": exc.source_id,
                "chunk_count": exc.chunk_count,
                "status": exc.status,
                "crop_names": exc.crop_names,
            },
        )
    except LoaderValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.as_detail(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return IngestResponse(
        source_id=result.source_id,
        chunk_count=result.chunk_count,
        status=result.status,
    )
