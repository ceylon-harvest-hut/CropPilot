from pydantic import BaseModel

from app.domains.ingestion.schemas import CropItemResponse, CropListResponse

__all__ = ["CropItemResponse", "CropListResponse"]


class ChunkItemResponse(BaseModel):
    chunk_id: str
    crop_tag: str
    source_uri: str
    section_name: str
    page_number: int
    text_preview: str


class ChunkListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    chunks: list[ChunkItemResponse]


class SourceItemResponse(BaseModel):
    source_id: int
    origin_url: str
    status: str
    crop_names: list[str]


class SourceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    sources: list[SourceItemResponse]
