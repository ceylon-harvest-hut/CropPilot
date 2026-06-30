from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.debug.dependencies import (
    get_chunk_catalog,
    get_graph_read_catalog,
    get_source_catalog,
)
from app.domains.debug.graph_data import GraphCropNode
from app.domains.debug.graph_repositories import GraphReadRepository
from app.domains.debug.repositories import ChunkCatalogRepository, SourceCatalogRepository
from app.domains.debug.schemas import (
    ChunkItemResponse,
    ChunkListResponse,
    CropItemResponse,
    CropListResponse,
    GraphCropDetailResponse,
    GraphCropListResponse,
    GraphCropNodeResponse,
    GraphCropSummaryResponse,
    GraphDiseaseResponse,
    GraphFertilizerResponse,
    GraphPestResponse,
    SourceItemResponse,
    SourceListResponse,
)
from app.infrastructure.config import Settings, get_settings

router = APIRouter()


def _check_debug_enabled(settings: Settings = Depends(get_settings)) -> None:
    if not settings.debug_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _graph_crop_node_response(node: GraphCropNode) -> GraphCropNodeResponse:
    return GraphCropNodeResponse(
        source_uri=node.source_uri,
        name=node.name,
        manifest_crop_name=node.manifest_crop_name,
        scientific_name=node.scientific_name,
        altitude_min_m=node.altitude_min_m,
        altitude_max_m=node.altitude_max_m,
        temp_min_c=node.temp_min_c,
        temp_max_c=node.temp_max_c,
        rainfall_min_mm=node.rainfall_min_mm,
        rainfall_max_mm=node.rainfall_max_mm,
        ph_min=node.ph_min,
        ph_max=node.ph_max,
        pit_length_cm=node.pit_length_cm,
        pit_width_cm=node.pit_width_cm,
        row_distance_cm=node.row_distance_cm,
        plant_distance_cm=node.plant_distance_cm,
        expected_harvest_kg_per_ha=node.expected_harvest_kg_per_ha,
        days_to_maturity=node.days_to_maturity,
        nursery_period_days=node.nursery_period_days,
        seed_amount_per_ha=node.seed_amount_per_ha,
        seed_metric_type=node.seed_metric_type,
        growing_areas=node.growing_areas,
        growing_seasons=node.growing_seasons,
        varieties=node.varieties,
        soil_types=node.soil_types,
        fertilizer_schedule=[
            GraphFertilizerResponse(**vars(item)) for item in node.fertilizer_schedule
        ],
        pests=[GraphPestResponse(**vars(item)) for item in node.pests],
        diseases=[GraphDiseaseResponse(**vars(item)) for item in node.diseases],
    )


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
        limit=limit,
        offset=offset,
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
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    catalog: SourceCatalogRepository = Depends(get_source_catalog),
) -> SourceListResponse:
    sources, total = catalog.list_sources(
        crop_name=crop_name,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    items = [SourceItemResponse(**vars(s)) for s in sources]
    return SourceListResponse(total=total, limit=limit, offset=offset, sources=items)


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


@router.get(
    "/graph/crops",
    response_model=GraphCropListResponse,
    summary="List crops from Neo4j graph",
    dependencies=[Depends(_check_debug_enabled)],
)
def list_graph_crops(
    catalog: GraphReadRepository = Depends(get_graph_read_catalog),
) -> GraphCropListResponse:
    try:
        summaries = catalog.list_crop_summaries()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Graph read failed: {exc}",
        ) from exc
    crops = [GraphCropSummaryResponse(**vars(item)) for item in summaries]
    return GraphCropListResponse(total=len(crops), crops=crops)


@router.get(
    "/graph/crops/{crop_name}",
    response_model=GraphCropDetailResponse,
    summary="Get crop graph detail from Neo4j",
    dependencies=[Depends(_check_debug_enabled)],
)
def get_graph_crop_detail(
    crop_name: str,
    catalog: GraphReadRepository = Depends(get_graph_read_catalog),
) -> GraphCropDetailResponse:
    try:
        detail = catalog.get_crop_detail(crop_name)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Graph read failed: {exc}",
        ) from exc
    return GraphCropDetailResponse(
        name=detail.name,
        nodes=[_graph_crop_node_response(node) for node in detail.nodes],
    )
