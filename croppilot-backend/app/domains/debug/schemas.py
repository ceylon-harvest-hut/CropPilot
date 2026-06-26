from pydantic import BaseModel


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


class CropItemResponse(BaseModel):
    crop_id: int
    name: str
    botanical_name: str | None


class CropListResponse(BaseModel):
    total: int
    crops: list[CropItemResponse]
