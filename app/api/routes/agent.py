from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    user_message: str


class ChatResponse(BaseModel):
    response: str
    messages: list[dict[str, Any]]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    from app.agent.agent import chat as agent_chat

    # Append the new user message to history
    messages = list(request.messages)
    messages.append({"role": "user", "content": request.user_message})

    response_text, updated_messages = await agent_chat(messages)
    return ChatResponse(response=response_text, messages=updated_messages)
