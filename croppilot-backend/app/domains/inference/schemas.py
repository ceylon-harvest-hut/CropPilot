from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    crop_name: str | None = None


class SourceChunkResponse(BaseModel):
    chunk_id: str
    section_name: str
    text_preview: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunkResponse]
