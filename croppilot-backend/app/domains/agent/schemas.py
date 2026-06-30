from pydantic import BaseModel, Field, field_validator


class AskAgentRequest(BaseModel):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class ToolCallResponse(BaseModel):
    name: str
    arguments: dict[str, object]
    result: str


class AskAgentResponse(BaseModel):
    answer: str
    tools_used: list[ToolCallResponse]
