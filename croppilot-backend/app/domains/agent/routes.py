from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.agent.dependencies import get_agent_service
from app.domains.agent.schemas import AskAgentRequest, AskAgentResponse, ToolCallResponse
from app.domains.agent.service import AgentService

router = APIRouter()


@router.post(
    "/ask-agent",
    status_code=status.HTTP_200_OK,
    response_model=AskAgentResponse,
    summary="Ask a question using the graph agent",
)
async def ask_agent(
    body: AskAgentRequest,
    service: AgentService = Depends(get_agent_service),
) -> AskAgentResponse:
    try:
        result = service.ask(body.question)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ask agent failed: {exc}",
        ) from exc

    return AskAgentResponse(
        answer=result.answer,
        tools_used=[
            ToolCallResponse(
                name=tool.name,
                arguments=tool.arguments,
                result=tool.result,
            )
            for tool in result.tools_used
        ],
    )
