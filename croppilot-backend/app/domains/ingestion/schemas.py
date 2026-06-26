from typing import Literal

from pydantic import BaseModel


class IngestRequest(BaseModel):
    source_uri: str
    crop_name: str
    source_type: Literal["file", "web_url"] | None = None
    loader: str | None = None
    replace_existing: bool = False


class IngestResponse(BaseModel):
    source_id: int
    chunk_count: int
    status: str
    replaced: bool = False
    previous_chunk_count: int = 0
