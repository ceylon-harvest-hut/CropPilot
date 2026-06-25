from pydantic import BaseModel


class IngestRequest(BaseModel):
    source_uri: str
    crop_name: str


class IngestResponse(BaseModel):
    source_id: int
    chunk_count: int
    status: str
