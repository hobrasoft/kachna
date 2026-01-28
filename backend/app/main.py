import os
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="kachna-api", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8097").rstrip("/")
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "60"))
LLM_API_KEY = os.getenv("LLM_API_KEY")


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


def _llm_headers() -> dict:
    if not LLM_API_KEY:
        return {}
    return {"Authorization": f"Bearer {LLM_API_KEY}"}


async def _forward_to_llm(path: str, payload: Optional[dict] = None) -> dict:
    url = f"{LLM_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_S) as client:
            if payload is None:
                response = await client.get(url, headers=_llm_headers())
            else:
                response = await client.post(url, json=payload, headers=_llm_headers())
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"LLM error: {response.text}")

    return response.json()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    data = await _forward_to_llm("/v1/models")
    return ModelsResponse.model_validate(data)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(payload: ChatCompletionRequest) -> ChatCompletionResponse:
    data = await _forward_to_llm("/v1/chat/completions", payload.model_dump())
    return ChatCompletionResponse.model_validate(data)
