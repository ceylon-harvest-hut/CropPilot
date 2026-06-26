from typing import Any, Literal

from pydantic import BaseModel, Field


class LoaderOption(BaseModel):
    name: str
    label: str
    source_types: list[str]


class LabOptions(BaseModel):
    source_types: list[str]
    loaders: list[LoaderOption]
    chunkers: list[str]
    embedders: list[str]


class LoadRequest(BaseModel):
    source_uri: str
    source_type: Literal["file", "web_url"]
    loader: str = Field(..., min_length=1)


class DocumentItem(BaseModel):
    text: str
    metadata: dict[str, Any]


class LoadResponse(BaseModel):
    documents: list[DocumentItem]
    source_uri: str
    source_type: str
    loader: str
    media_type: str
    char_count: int
    line_count: int


class ChunkRequest(BaseModel):
    documents: list[DocumentItem]
    crop_name: str
    chunker: str = "section"
    chunk_size: int = 500
    chunk_overlap: int = 50


class ChunkItem(BaseModel):
    index: int
    section_name: str
    page_number: int
    char_count: int
    text: str


class ChunkResponse(BaseModel):
    chunk_count: int
    chunks: list[ChunkItem]


class CommitRequest(BaseModel):
    source_uri: str
    crop_name: str
    chunks: list[ChunkItem]
    embedder: str = "fast"
    replace_existing: bool = False


class CommitResponse(BaseModel):
    source_id: int
    chunk_count: int
    status: str
    replaced: bool = False
    previous_chunk_count: int = 0


class SourceExistsResponse(BaseModel):
    exists: bool
    source_id: int | None = None
    chunk_count: int | None = None
    status: str | None = None
    crop_names: list[str] = []
