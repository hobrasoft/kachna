from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="kachna-api", version="0.1.0")


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    owned_by: str = "local"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelCard]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    model: str
    choices: List[ChatChoice]


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    models = [
        ModelCard(id="llama-local-7b"),
        ModelCard(id="llama-local-13b"),
    ]
    return ModelsResponse(data=models)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(payload: ChatCompletionRequest) -> ChatCompletionResponse:
    last_message = payload.messages[-1].content if payload.messages else ""
    reply = ChatMessage(role="assistant", content=f"Echo: {last_message}")
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid4().hex}",
        model=payload.model,
        choices=[ChatChoice(index=0, message=reply)],
    )
