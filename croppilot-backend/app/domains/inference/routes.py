from fastapi import APIRouter, Depends, status

from app.domains.inference.dependencies import get_inference_service
from app.domains.inference.schemas import AskRequest, AskResponse, SourceChunkResponse
from app.domains.inference.service import InferenceService

router = APIRouter()


@router.post(
    "/ask",
    status_code=status.HTTP_200_OK,
    response_model=AskResponse,
    summary="Ask a question using RAG",
)
async def ask(
    body: AskRequest,
    service: InferenceService = Depends(get_inference_service),
) -> AskResponse:
    result = service.ask(body.question, crop_tag=body.crop_name)
    return AskResponse(
        answer=result.text,
        sources=[
            SourceChunkResponse(
                chunk_id=chunk.chunk_id,
                section_name=chunk.section_name,
                text_preview=chunk.text_content[:150],
            )
            for chunk in result.sources
        ],
    )
