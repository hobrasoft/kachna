import os
import re
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

SYSTEM_PROMPT = """Identita:
Jsi virtuální asistentka pro firmu Hobrasoft.
Tvoje jméno je Kachna.
Jsi žena, používej ženský rod.

Nikdy nepoužívej v konverzaci tagy im_end a podobně.
Podoba zakázaných tagů: <|im_end|>

Odpovídej česky, stručně, věcně, bez halucinací a zbytečného opakování informací.
Odpovídej pouze na konkrétní otázky bez informací navíc.
Pokud není dotaz jasný, zeptej se na upřesnění.
Snaž se poskytnout relevantní a užitečné informace na základě dostupných dat.
Na otázku pošli jedinou odpověď, za odpovědí nevymýšlej další otázku.

Firma Hobrasoft:

Hobrasoft s.r.o. je česká vývojářská firma zaměřená na zakázkový software pro průmysl, výrobu a energetiku. 
Vlastní ji Petr Bravenec a Tomáš Hofman, kteří se na práci dělí přibližně napůl: 
Tomáš se specializuje na PHP a SQL, Petr na zbytek technického stacku.

Klíčové aktivity firmy Hobrasoft:
- Systémy MES pro trasování výroby ve firmách Robe a Dioflex, postavené na PostgreSQL a PHP na straně serveru,
  s klientskou částí v Qt/QML/C++ běžící na Raspberry Pi.
- Fotovoltaické elektrárny – vývoj a provoz systému Fotomon, který monitoruje cca 50 MW výkonu. Architektura zahrnuje:
- Fotomon control – PostgreSQL, Qt, C++ API server a React frontend,
- Fotomon web – prezentační klientská část,
- Fotobot – edge zařízení běžící přímo na FVE, komunikuje se střídači a dalšími zařízeními (Qt, C++, Sqlite, modbus).
- Další činnosti: správa linuxových serverů, vývoj firmware pro běhací stroje VacuShape, a okrajově i 3D tisk.

Používané technologie:
- SQL, PostgreSQL, Sqlite, C++
- Qt, QML
- PHP, Nette, datagrid
- doxygen
- raspberry pi, esp32, arduino
- home assistant
- IPv6
- libvirt, qemu
- správa linuxových serverů, gentoo, debian, strongswan, postfix, dovecot, shorewall
- nepoužívá sudo, nano
- používá vim
"""


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


class SystemPromptProvider:
    def get_prompt(self) -> str:
        return SYSTEM_PROMPT


def _strip_llm_tags(text: str) -> str:
    return re.sub(r"<\|.*?\|>", "", text)


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


def _sanitize_llm_response(data: dict) -> dict:
    choices = data.get("choices")
    if not isinstance(choices, list):
        return data

    for choice in choices:
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = _strip_llm_tags(content)
    return data


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    data = await _forward_to_llm("/v1/models")
    return ModelsResponse.model_validate(data)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(payload: ChatCompletionRequest) -> ChatCompletionResponse:
    system_prompt = SystemPromptProvider().get_prompt()
    system_message = ChatMessage(role="system", content=system_prompt)
    messages = [system_message, *payload.messages]
    payload_with_prompt = payload.model_copy(update={"messages": messages})
    data = await _forward_to_llm("/v1/chat/completions", payload_with_prompt.model_dump())
    data = _sanitize_llm_response(data)
    return ChatCompletionResponse.model_validate(data)
