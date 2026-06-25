from pydantic import BaseModel


class LabOptions(BaseModel):
    loaders: list[str]
    chunkers: list[str]
    embedders: list[str]


class LoadRequest(BaseModel):
    source_uri: str
    loader: str = "text"


class LoadResponse(BaseModel):
    text: str
    source_uri: str
    media_type: str
    char_count: int
    line_count: int


class ChunkRequest(BaseModel):
    text: str
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


class CommitResponse(BaseModel):
    source_id: int
    chunk_count: int
    status: str
