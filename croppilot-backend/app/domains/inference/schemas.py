from typing import Literal

from pydantic import BaseModel, Field, field_validator

AskTemplateName = Literal["context_only", "hybrid"]


class AskRequest(BaseModel):
    question: str
    crop_name: str = Field(min_length=1, description="Crop to scope the search to (required).")
    template: AskTemplateName | None = None

    @field_validator("crop_name")
    @classmethod
    def crop_name_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("crop_name must not be blank")
        return stripped


class PromptTemplateOptionResponse(BaseModel):
    name: AskTemplateName
    label: str
    description: str


class AskTemplatesResponse(BaseModel):
    templates: list[PromptTemplateOptionResponse]
    default_template: AskTemplateName


class ReferenceDocumentResponse(BaseModel):
    source_uri: str
    crop_name: str
    title: str
    excerpt: str
    source_type: Literal["file", "web_url"]


class AskResponse(BaseModel):
    answer: str
    references: list[ReferenceDocumentResponse]
    template: AskTemplateName = Field(
        description="Prompt template used to generate the answer.",
    )
