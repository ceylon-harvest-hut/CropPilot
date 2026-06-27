from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.inference.dependencies import get_inference_service
from app.domains.inference.schemas import (
    AskRequest,
    AskResponse,
    AskTemplatesResponse,
    PromptTemplateOptionResponse,
    ReferenceDocumentResponse,
)
from app.domains.inference.service import InferenceService
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.llm.prompt_catalog import (
    list_prompt_template_options,
    resolve_template_name,
)

router = APIRouter()


@router.get(
    "/ask/templates",
    status_code=status.HTTP_200_OK,
    response_model=AskTemplatesResponse,
    summary="List available Ask prompt templates",
)
async def list_ask_templates(
    settings: Settings = Depends(get_settings),
) -> AskTemplatesResponse:
    default = resolve_template_name(settings.default_ask_template)
    return AskTemplatesResponse(
        templates=[
            PromptTemplateOptionResponse(
                name=option.name,  # type: ignore[arg-type]
                label=option.label,
                description=option.description,
            )
            for option in list_prompt_template_options()
        ],
        default_template=default,  # type: ignore[arg-type]
    )


@router.post(
    "/ask",
    status_code=status.HTTP_200_OK,
    response_model=AskResponse,
    summary="Ask a question using RAG",
)
async def ask(
    body: AskRequest,
    service: InferenceService = Depends(get_inference_service),
    settings: Settings = Depends(get_settings),
) -> AskResponse:
    try:
        template = resolve_template_name(body.template, default=settings.default_ask_template)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = service.ask(body.question, crop_tag=body.crop_name, template=template)
    return AskResponse(
        answer=result.text,
        template=template,  # type: ignore[arg-type]
        references=[
            ReferenceDocumentResponse(
                source_uri=ref.source_uri,
                crop_name=ref.crop_name,
                title=ref.title,
                excerpt=ref.excerpt,
                source_type=ref.source_type,  # type: ignore[arg-type]
            )
            for ref in result.references
        ],
    )
