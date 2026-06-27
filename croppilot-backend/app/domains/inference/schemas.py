from typing import Literal

from pydantic import BaseModel, Field

AskTemplateName = Literal["context_only", "hybrid"]


class AskRequest(BaseModel):
    question: str
    crop_name: str | None = None
    template: AskTemplateName | None = None


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
