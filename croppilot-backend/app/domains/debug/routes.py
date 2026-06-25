from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.debug.dependencies import get_chunk_catalog, get_source_catalog
from app.domains.debug.repositories import ChunkCatalogRepository, SourceCatalogRepository
from app.domains.debug.schemas import (
    ChunkItemResponse,
    ChunkListResponse,
    CropItemResponse,
    CropListResponse,
    SourceItemResponse,
    SourceListResponse,
)
from app.infrastructure.config import Settings, get_settings

router = APIRouter()


def _check_debug_enabled(settings: Settings = Depends(get_settings)) -> None:
    if not settings.debug_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get(
    "/chunks",
    response_model=ChunkListResponse,
    summary="List indexed chunks from Chroma",
    dependencies=[Depends(_check_debug_enabled)],
)
def list_chunks(
    crop_name: str | None = Query(default=None),
    source_uri: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    catalog: ChunkCatalogRepository = Depends(get_chunk_catalog),
) -> ChunkListResponse:
    chunks, total = catalog.list_chunks(
        crop_tag=crop_name,
        source_uri=source_uri,
        limit=limit,
        offset=offset,
    )
    return ChunkListResponse(
        total=total,
        chunks=[ChunkItemResponse(**vars(c)) for c in chunks],
    )


@router.get(
    "/sources",
    response_model=SourceListResponse,
    summary="List knowledge sources from SQLite",
    dependencies=[Depends(_check_debug_enabled)],
)
def list_sources(
    crop_name: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    catalog: SourceCatalogRepository = Depends(get_source_catalog),
) -> SourceListResponse:
    sources = catalog.list_sources(crop_name=crop_name, status=status_filter)
    items = [SourceItemResponse(**vars(s)) for s in sources]
    return SourceListResponse(total=len(items), sources=items)


@router.get(
    "/crops",
    response_model=CropListResponse,
    summary="List crops from SQLite",
    dependencies=[Depends(_check_debug_enabled)],
)
def list_crops(
    catalog: SourceCatalogRepository = Depends(get_source_catalog),
) -> CropListResponse:
    crops = catalog.list_crops()
    items = [CropItemResponse(**vars(c)) for c in crops]
    return CropListResponse(total=len(items), crops=items)
