import json
import re
from datetime import datetime
from typing import Any, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import BackendConfig
from .db import load_database

app = FastAPI(title="kachna-api", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=BackendConfig.corsAllowOrigins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
CHAT_BASE_URL = BackendConfig.chatBaseUrl()
EMBEDDING_BASE_URL = BackendConfig.embeddingBaseUrl()
CHAT_TIMEOUT_S = BackendConfig.chatTimeoutSeconds()
EMBEDDING_TIMEOUT_S = BackendConfig.embeddingTimeoutSeconds()
CHAT_API_KEY = BackendConfig.chatApiKey()
EMBEDDING_API_KEY = BackendConfig.embeddingApiKey()
SIMILARITY_THRESHOLD = BackendConfig.embeddingSimilarityThreshold()
DB = load_database()



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


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    user: int
    title: str


class ConversationDeleteRequest(BaseModel):
    user: int


class ConversationResponse(BaseModel):
    conversation: int
    user: int
    date: datetime
    title: str


class MessageResponse(BaseModel):
    message: int
    conversation: int
    role: str
    date: datetime
    text: str
    token_count: Optional[int] = None


class FunctionMatch(BaseModel):
    function: int
    name: str
    description: str
    active: bool
    type: str
    script: str
    similarity: float


class TopicMatch(BaseModel):
    topic: int
    topic_category: int
    text: str
    similarity: float


class ChatTurnRequest(BaseModel):
    user: int
    model: str
    content: str


class ChatTurnResponse(BaseModel):
    conversation: ConversationResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
    matched_functions: List[FunctionMatch] = Field(default_factory=list)
    matched_topics: List[TopicMatch] = Field(default_factory=list)


class EmbeddingRequest(BaseModel):
    model: str
    input: Any
    user: Optional[str] = None


class LoginRequest(BaseModel):
    login: str
    password: str


class UserBase(BaseModel):
    name: str
    login: str


class UserCreate(UserBase):
    password: str
    roles: Optional[List[int]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[List[int]] = None


class UserResponse(UserBase):
    user: int


class UserRoleSummary(BaseModel):
    user_role: int
    abbr: str
    name: str


class UserWithRoles(UserResponse):
    roles: List[UserRoleSummary]


class RoleBase(BaseModel):
    system_prompt: int
    abbr: str
    name: str
    admin: bool = False


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    system_prompt: Optional[int] = None
    abbr: Optional[str] = None
    name: Optional[str] = None
    admin: Optional[bool] = None


class RoleResponse(RoleBase):
    user_role: int


class SystemPromptBase(BaseModel):
    name: str
    text: str


class SystemPromptUpdate(BaseModel):
    name: Optional[str] = None
    text: Optional[str] = None


class SystemPromptResponse(SystemPromptBase):
    system_prompt: int


class TopicCategoryBase(BaseModel):
    name: str
    description: str


class TopicCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TopicCategoryPolicy(BaseModel):
    user_role: int
    role_abbr: str
    role_name: str
    topic_policy: int
    policy_name: str
    policy: Optional[str] = None


class TopicCategoryResponse(TopicCategoryBase):
    topic_category: int
    policies: List[TopicCategoryPolicy] = Field(default_factory=list)


class TopicBase(BaseModel):
    topic_category: int
    text: str
    embedding: Optional[List[float]] = None


class TopicUpdate(BaseModel):
    topic_category: Optional[int] = None
    text: Optional[str] = None


class TopicResponse(TopicBase):
    topic: int
    embedding: List[float]


class FunctionBase(BaseModel):
    name: str
    description: str
    active: bool = True
    type: str
    script: str
    user_roles: List[int] = Field(default_factory=list)


class FunctionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    type: Optional[str] = None
    script: Optional[str] = None
    user_roles: Optional[List[int]] = None


class FunctionResponse(FunctionBase):
    function: int
    role_abbrs: List[str] = Field(default_factory=list)


class FunctionQuestionBase(BaseModel):
    function: int
    text: str


class FunctionQuestionUpdate(BaseModel):
    function: Optional[int] = None
    text: Optional[str] = None


class FunctionQuestionResponse(FunctionQuestionBase):
    function_question: int


class LoginRole(BaseModel):
    user_role: int
    system_prompt: int
    abbr: str
    name: str
    admin: bool


class LoginResponse(BaseModel):
    user: int
    name: str
    login: str
    roles: List[LoginRole]


async def _build_system_prompt_for_user(user_id: int) -> str:
    rows = await DB.list_user_system_prompts(user_id)
    prompts = [row["text"].strip() for row in rows if row["text"] and row["text"].strip()]
    if not prompts:
        raise HTTPException(
            status_code=400,
            detail="Uživatel nemá přiřazený systémový prompt.",
        )
    return "\n\n".join(prompts)


def _vector_from_list(values: List[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


def _parse_vector(value: Any) -> List[float]:
    if value is None:
        return []
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip().strip("[]")
        if not stripped:
            return []
        return [float(item) for item in stripped.split(",")]
    return []


def _parse_policies(value: Any) -> List["TopicCategoryPolicy"]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    policies: List[TopicCategoryPolicy] = []
    for item in value:
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                continue
        if isinstance(item, dict):
            policies.append(TopicCategoryPolicy(**item))
    return policies


def _ensure_row(row: Any, message: str) -> Any:
    if row is None:
        raise HTTPException(status_code=404, detail=message)
    return row


def _strip_llm_tags(text: str) -> str:
    return re.sub(r"<\|.*?\|>", "", text)


def _conversation_title_from_text(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "Konverzace"
    if len(cleaned) > 60:
        return f"{cleaned[:57].rstrip()}…"
    return cleaned


def _llm_headers(api_key: str | None) -> dict:
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


async def _forward_to_llm(
    base_url: str,
    path: str,
    timeout_s: float,
    api_key: str | None,
    payload: Optional[dict] = None,
) -> dict:
    url = f"{base_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            if payload is None:
                response = await client.get(url, headers=_llm_headers(api_key))
            else:
                response = await client.post(url, json=payload, headers=_llm_headers(api_key))
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


_EMBEDDING_MODEL_ID: Optional[str] = None


async def _get_embedding_model_id() -> str:
    global _EMBEDDING_MODEL_ID
    if _EMBEDDING_MODEL_ID:
        return _EMBEDDING_MODEL_ID
    data = await _forward_to_llm(
        EMBEDDING_BASE_URL,
        "/v1/models",
        EMBEDDING_TIMEOUT_S,
        EMBEDDING_API_KEY,
    )
    models = data.get("data")
    if not isinstance(models, list):
        raise HTTPException(status_code=502, detail="Embedding modely nejsou dostupné.")
    for model in models:
        if isinstance(model, dict):
            model_id = model.get("id")
            if isinstance(model_id, str) and model_id:
                _EMBEDDING_MODEL_ID = model_id
                return model_id
    raise HTTPException(status_code=502, detail="Embedding model nebyl nalezen.")


async def _create_embedding(text: str) -> List[float]:
    model_id = await _get_embedding_model_id()
    payload = EmbeddingRequest(model=model_id, input=text).model_dump()
    data = await _forward_to_llm(
        EMBEDDING_BASE_URL,
        "/v1/embeddings",
        EMBEDDING_TIMEOUT_S,
        EMBEDDING_API_KEY,
        payload,
    )
    entries = data.get("data")
    if not isinstance(entries, list) or not entries:
        raise HTTPException(status_code=502, detail="Embedding nebyl vrácen.")
    embedding = entries[0].get("embedding") if isinstance(entries[0], dict) else None
    if not isinstance(embedding, list):
        raise HTTPException(status_code=502, detail="Embedding má neplatný formát.")
    return [float(value) for value in embedding]


@app.on_event("startup")
async def startup_db() -> None:
    await DB.connect()


@app.on_event("shutdown")
async def shutdown_db() -> None:
    await DB.disconnect()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.post("/v1/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    user_row = await DB.get_user_by_login(payload.login)
    if user_row is None or user_row["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Neplatné přihlašovací údaje.")

    role_rows = await DB.get_user_roles(user_row["user"])
    roles = [
        LoginRole(
            user_role=row["user_role"],
            system_prompt=row["system_prompt"],
            abbr=row["abbr"],
            name=row["name"],
            admin=row["admin"],
        )
        for row in role_rows
    ]
    return LoginResponse(
        user=user_row["user"],
        name=user_row["name"],
        login=user_row["login"],
        roles=roles,
    )


@app.get("/v1/users", response_model=List[UserWithRoles])
async def list_users() -> List[UserWithRoles]:
    rows = await DB.list_users()
    response: List[UserWithRoles] = []
    for row in rows:
        roles = await DB.get_user_roles(row["user"])
        response.append(
            UserWithRoles(
                user=row["user"],
                name=row["name"],
                login=row["login"],
                roles=[
                    UserRoleSummary(
                        user_role=role["user_role"],
                        abbr=role["abbr"],
                        name=role["name"],
                    )
                    for role in roles
                ],
            )
        )
    return response


@app.post("/v1/users", response_model=UserResponse)
async def create_user(payload: UserCreate) -> UserResponse:
    row = await DB.create_user(payload.name, payload.login, payload.password)
    row = _ensure_row(row, "Uživatel nebyl vytvořen.")
    if payload.roles is not None:
        await DB.replace_user_roles(row["user"], payload.roles)
    return UserResponse(user=row["user"], name=row["name"], login=row["login"])


@app.get("/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    row = await DB.get_user(user_id)
    row = _ensure_row(row, "Uživatel nenalezen.")
    return UserResponse(user=row["user"], name=row["name"], login=row["login"])


@app.put("/v1/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdate) -> UserResponse:
    current = await DB.get_user_with_password(user_id)
    current = _ensure_row(current, "Uživatel nenalezen.")
    name = payload.name if payload.name is not None else current["name"]
    login_value = payload.login if payload.login is not None else current["login"]
    password = payload.password if payload.password is not None else current["password"]
    row = await DB.update_user(user_id, name, login_value, password)
    row = _ensure_row(row, "Uživatel nebyl upraven.")
    if payload.roles is not None:
        await DB.replace_user_roles(user_id, payload.roles)
    return UserResponse(user=row["user"], name=row["name"], login=row["login"])


@app.delete("/v1/users/{user_id}")
async def delete_user(user_id: int) -> dict:
    result = await DB.delete_user(user_id)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Uživatel nenalezen.")
    return {"status": "ok"}


@app.get("/v1/users/{user_id}/conversations", response_model=List[ConversationResponse])
async def list_conversations(user_id: int) -> List[ConversationResponse]:
    rows = await DB.list_conversations(user_id)
    return [
        ConversationResponse(
            conversation=row["conversation"],
            user=row["user"],
            date=row["date"],
            title=row["title"],
        )
        for row in rows
    ]


@app.post("/v1/users/{user_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    user_id: int,
    payload: ConversationCreateRequest,
) -> ConversationResponse:
    user_row = await DB.get_user(user_id)
    _ensure_row(user_row, "Uživatel nenalezen.")
    title = payload.title or "Nová konverzace"
    row = await DB.create_conversation(user_id, title)
    row = _ensure_row(row, "Konverzace nebyla vytvořena.")
    system_prompt = await _build_system_prompt_for_user(user_id)
    system_embedding = await _create_embedding(system_prompt)
    await DB.create_message(
        row["conversation"],
        "system",
        system_prompt,
        None,
        _vector_from_list(system_embedding),
    )
    return ConversationResponse(
        conversation=row["conversation"],
        user=row["user"],
        date=row["date"],
        title=row["title"],
    )


@app.put("/v1/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation_title(
    conversation_id: int,
    payload: ConversationUpdateRequest,
) -> ConversationResponse:
    conversation = await DB.get_conversation(conversation_id)
    conversation = _ensure_row(conversation, "Konverzace nenalezena.")
    if conversation["removed"]:
        raise HTTPException(status_code=404, detail="Konverzace byla odstraněna.")
    if conversation["user"] != payload.user:
        raise HTTPException(status_code=403, detail="Konverzace nepatří uživateli.")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Název nesmí být prázdný.")
    updated = await DB.update_conversation_title(conversation_id, title)
    updated = _ensure_row(updated, "Konverzace nenalezena.")
    return ConversationResponse(
        conversation=updated["conversation"],
        user=updated["user"],
        date=updated["date"],
        title=updated["title"],
    )


@app.delete("/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    payload: ConversationDeleteRequest,
) -> dict:
    conversation = await DB.get_conversation(conversation_id)
    conversation = _ensure_row(conversation, "Konverzace nenalezena.")
    if conversation["removed"]:
        raise HTTPException(status_code=404, detail="Konverzace byla odstraněna.")
    if conversation["user"] != payload.user:
        raise HTTPException(status_code=403, detail="Konverzace nepatří uživateli.")
    result = await DB.delete_conversation(conversation_id)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Konverzace nenalezena.")
    return {"status": "ok"}


@app.get("/v1/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_conversation_messages(conversation_id: int) -> List[MessageResponse]:
    conversation = await DB.get_conversation(conversation_id)
    conversation = _ensure_row(conversation, "Konverzace nenalezena.")
    if conversation["removed"]:
        raise HTTPException(status_code=404, detail="Konverzace byla odstraněna.")
    rows = await DB.list_messages(conversation_id)
    return [
        MessageResponse(
            message=row["message"],
            conversation=row["conversation"],
            role=row["role"],
            date=row["date"],
            text=row["text"],
            token_count=row["token_count"],
        )
        for row in rows
    ]


@app.post(
    "/v1/conversations/{conversation_id}/chat",
    response_model=ChatTurnResponse,
)
async def create_conversation_chat_turn(
    conversation_id: int,
    payload: ChatTurnRequest,
) -> ChatTurnResponse:
    conversation = await DB.get_conversation(conversation_id)
    conversation = _ensure_row(conversation, "Konverzace nenalezena.")
    if conversation["user"] != payload.user:
        raise HTTPException(status_code=403, detail="Konverzace nepatří uživateli.")
    if conversation["removed"]:
        raise HTTPException(status_code=404, detail="Konverzace byla odstraněna.")

    user_embedding = await _create_embedding(payload.content)
    user_embedding_value = _vector_from_list(user_embedding)
    user_row = await DB.create_message(
        conversation_id,
        "user",
        payload.content,
        None,
        user_embedding_value,
    )
    user_row = _ensure_row(user_row, "Zpráva nebyla uložena.")

    matched_function_rows = await DB.find_matching_functions(
        user_embedding_value,
        SIMILARITY_THRESHOLD,
    )
    matched_topic_rows = await DB.find_matching_topics(
        user_embedding_value,
        SIMILARITY_THRESHOLD,
    )

    if conversation["title"] == "Nová konverzace":
        updated_title = _conversation_title_from_text(payload.content)
        updated_conversation = await DB.update_conversation_title(
            conversation_id,
            updated_title,
        )
        if updated_conversation is not None:
            conversation = updated_conversation

    history_rows = await DB.list_messages(conversation_id)
    history_messages = [
        ChatMessage(role=row["role"], content=row["text"]) for row in history_rows
    ]
    data = await _forward_to_llm(
        CHAT_BASE_URL,
        "/v1/chat/completions",
        CHAT_TIMEOUT_S,
        CHAT_API_KEY,
        ChatCompletionRequest(model=payload.model, messages=history_messages).model_dump(),
    )
    data = _sanitize_llm_response(data)
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=502, detail="Odpověď je prázdná.")
    reply = content.strip()
    assistant_embedding = await _create_embedding(reply)
    assistant_row = await DB.create_message(
        conversation_id,
        "assistant",
        reply,
        None,
        _vector_from_list(assistant_embedding),
    )
    assistant_row = _ensure_row(assistant_row, "Odpověď nebyla uložena.")

    return ChatTurnResponse(
        conversation=ConversationResponse(
            conversation=conversation["conversation"],
            user=conversation["user"],
            date=conversation["date"],
            title=conversation["title"],
        ),
        user_message=MessageResponse(
            message=user_row["message"],
            conversation=user_row["conversation"],
            role=user_row["role"],
            date=user_row["date"],
            text=user_row["text"],
            token_count=user_row["token_count"],
        ),
        assistant_message=MessageResponse(
            message=assistant_row["message"],
            conversation=assistant_row["conversation"],
            role=assistant_row["role"],
            date=assistant_row["date"],
            text=assistant_row["text"],
            token_count=assistant_row["token_count"],
        ),
        matched_functions=[
            FunctionMatch(
                function=row["function"],
                name=row["name"],
                description=row["description"],
                active=row["active"],
                type=row["type"],
                script=row["script"],
                similarity=float(row["similarity"]),
            )
            for row in matched_function_rows
        ],
        matched_topics=[
            TopicMatch(
                topic=row["topic"],
                topic_category=row["topic_category"],
                text=row["text"],
                similarity=float(row["similarity"]),
            )
            for row in matched_topic_rows
        ],
    )


@app.get("/v1/user-roles", response_model=List[RoleResponse])
async def list_roles() -> List[RoleResponse]:
    rows = await DB.list_roles()
    return [
        RoleResponse(
            user_role=row["user_role"],
            system_prompt=row["system_prompt"],
            abbr=row["abbr"],
            name=row["name"],
            admin=row["admin"],
        )
        for row in rows
    ]


@app.post("/v1/user-roles", response_model=RoleResponse)
async def create_role(payload: RoleCreate) -> RoleResponse:
    row = await DB.create_role(
        payload.system_prompt,
        payload.abbr,
        payload.name,
        payload.admin,
    )
    row = _ensure_row(row, "Role nebyla vytvořena.")
    return RoleResponse(
        user_role=row["user_role"],
        system_prompt=row["system_prompt"],
        abbr=row["abbr"],
        name=row["name"],
        admin=row["admin"],
    )


@app.get("/v1/user-roles/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int) -> RoleResponse:
    row = await DB.get_role(role_id)
    row = _ensure_row(row, "Role nenalezena.")
    return RoleResponse(
        user_role=row["user_role"],
        system_prompt=row["system_prompt"],
        abbr=row["abbr"],
        name=row["name"],
        admin=row["admin"],
    )


@app.put("/v1/user-roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: int, payload: RoleUpdate) -> RoleResponse:
    current = await DB.get_role(role_id)
    current = _ensure_row(current, "Role nenalezena.")
    system_prompt = (
        payload.system_prompt if payload.system_prompt is not None else current["system_prompt"]
    )
    abbr = payload.abbr if payload.abbr is not None else current["abbr"]
    name = payload.name if payload.name is not None else current["name"]
    admin = payload.admin if payload.admin is not None else current["admin"]
    row = await DB.update_role(role_id, system_prompt, abbr, name, admin)
    row = _ensure_row(row, "Role nebyla upravena.")
    return RoleResponse(
        user_role=row["user_role"],
        system_prompt=row["system_prompt"],
        abbr=row["abbr"],
        name=row["name"],
        admin=row["admin"],
    )


@app.delete("/v1/user-roles/{role_id}")
async def delete_role(role_id: int) -> dict:
    result = await DB.delete_role(role_id)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Role nenalezena.")
    return {"status": "ok"}


@app.get("/v1/system-prompts", response_model=List[SystemPromptResponse])
async def list_system_prompts() -> List[SystemPromptResponse]:
    rows = await DB.list_system_prompts()
    return [
        SystemPromptResponse(
            system_prompt=row["system_prompt"],
            name=row["name"],
            text=row["text"],
        )
        for row in rows
    ]


@app.post("/v1/system-prompts", response_model=SystemPromptResponse)
async def create_system_prompt(payload: SystemPromptBase) -> SystemPromptResponse:
    row = await DB.create_system_prompt(payload.name, payload.text)
    row = _ensure_row(row, "Prompt nebyl vytvořen.")
    return SystemPromptResponse(
        system_prompt=row["system_prompt"],
        name=row["name"],
        text=row["text"],
    )


@app.get("/v1/system-prompts/{system_prompt}", response_model=SystemPromptResponse)
async def get_system_prompt(system_prompt: int) -> SystemPromptResponse:
    row = await DB.get_system_prompt(system_prompt)
    row = _ensure_row(row, "Prompt nenalezen.")
    return SystemPromptResponse(
        system_prompt=row["system_prompt"],
        name=row["name"],
        text=row["text"],
    )


@app.put("/v1/system-prompts/{system_prompt}", response_model=SystemPromptResponse)
async def update_system_prompt(
    system_prompt: int,
    payload: SystemPromptUpdate,
) -> SystemPromptResponse:
    current = await DB.get_system_prompt(system_prompt)
    current = _ensure_row(current, "Prompt nenalezen.")
    name = payload.name if payload.name is not None else current["name"]
    text = payload.text if payload.text is not None else current["text"]
    row = await DB.update_system_prompt(system_prompt, name, text)
    row = _ensure_row(row, "Prompt nebyl upraven.")
    return SystemPromptResponse(
        system_prompt=row["system_prompt"],
        name=row["name"],
        text=row["text"],
    )


@app.delete("/v1/system-prompts/{system_prompt}")
async def delete_system_prompt(system_prompt: int) -> dict:
    result = await DB.delete_system_prompt(system_prompt)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Prompt nenalezen.")
    return {"status": "ok"}


@app.get("/v1/topic-categories", response_model=List[TopicCategoryResponse])
async def list_topic_categories() -> List[TopicCategoryResponse]:
    rows = await DB.list_topic_categories()
    return [
        TopicCategoryResponse(
            topic_category=row["topic_category"],
            name=row["name"],
            description=row["description"],
            policies=_parse_policies(row["policies"]),
        )
        for row in rows
    ]


@app.post("/v1/topic-categories", response_model=TopicCategoryResponse)
async def create_topic_category(payload: TopicCategoryBase) -> TopicCategoryResponse:
    row = await DB.create_topic_category(
        payload.name,
        payload.description,
    )
    row = _ensure_row(row, "Kategorie tématu nebyla vytvořena.")
    row = await DB.get_topic_category(row["topic_category"])
    row = _ensure_row(row, "Kategorie tématu nebyla načtena.")
    return TopicCategoryResponse(
        topic_category=row["topic_category"],
        name=row["name"],
        description=row["description"],
        policies=_parse_policies(row["policies"]),
    )


@app.get("/v1/topic-categories/{topic_category}", response_model=TopicCategoryResponse)
async def get_topic_category(topic_category: int) -> TopicCategoryResponse:
    row = await DB.get_topic_category(topic_category)
    row = _ensure_row(row, "Kategorie tématu nenalezena.")
    return TopicCategoryResponse(
        topic_category=row["topic_category"],
        name=row["name"],
        description=row["description"],
        policies=_parse_policies(row["policies"]),
    )


@app.put("/v1/topic-categories/{topic_category}", response_model=TopicCategoryResponse)
async def update_topic_category(
    topic_category: int,
    payload: TopicCategoryUpdate,
) -> TopicCategoryResponse:
    current = await DB.get_topic_category(topic_category)
    current = _ensure_row(current, "Kategorie tématu nenalezena.")
    name = payload.name if payload.name is not None else current["name"]
    description = payload.description if payload.description is not None else current["description"]
    row = await DB.update_topic_category(topic_category, name, description)
    row = _ensure_row(row, "Kategorie tématu nebyla upravena.")
    row = await DB.get_topic_category(topic_category)
    row = _ensure_row(row, "Kategorie tématu nebyla načtena.")
    return TopicCategoryResponse(
        topic_category=row["topic_category"],
        name=row["name"],
        description=row["description"],
        policies=_parse_policies(row["policies"]),
    )


@app.delete("/v1/topic-categories/{topic_category}")
async def delete_topic_category(topic_category: int) -> dict:
    result = await DB.delete_topic_category(topic_category)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Kategorie tématu nenalezena.")
    return {"status": "ok"}


@app.get("/v1/topics", response_model=List[TopicResponse])
async def list_topics() -> List[TopicResponse]:
    rows = await DB.list_topics()
    return [
        TopicResponse(
            topic=row["topic"],
            topic_category=row["topic_category"],
            text=row["text"],
            embedding=_parse_vector(row["embedding"]),
        )
        for row in rows
    ]


@app.post("/v1/topics", response_model=TopicResponse)
async def create_topic(payload: TopicBase) -> TopicResponse:
    embedding_list = await _create_embedding(payload.text)
    embedding_value = _vector_from_list(embedding_list)
    row = await DB.create_topic(payload.topic_category, payload.text, embedding_value)
    row = _ensure_row(row, "Téma nebylo vytvořeno.")
    return TopicResponse(
        topic=row["topic"],
        topic_category=row["topic_category"],
        text=row["text"],
        embedding=_parse_vector(row["embedding"]),
    )


@app.get("/v1/topics/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: int) -> TopicResponse:
    row = await DB.get_topic(topic_id)
    row = _ensure_row(row, "Téma nenalezeno.")
    return TopicResponse(
        topic=row["topic"],
        topic_category=row["topic_category"],
        text=row["text"],
        embedding=_parse_vector(row["embedding"]),
    )


@app.put("/v1/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: int, payload: TopicUpdate) -> TopicResponse:
    current = await DB.get_topic(topic_id)
    current = _ensure_row(current, "Téma nenalezeno.")
    topic_category = (
        payload.topic_category if payload.topic_category is not None else current["topic_category"]
    )
    text_value = payload.text if payload.text is not None else current["text"]
    embedding_list = await _create_embedding(text_value)
    embedding_value = _vector_from_list(embedding_list)
    row = await DB.update_topic(topic_id, topic_category, text_value, embedding_value)
    row = _ensure_row(row, "Téma nebylo upraveno.")
    return TopicResponse(
        topic=row["topic"],
        topic_category=row["topic_category"],
        text=row["text"],
        embedding=_parse_vector(row["embedding"]),
    )


@app.delete("/v1/topics/{topic_id}")
async def delete_topic(topic_id: int) -> dict:
    result = await DB.delete_topic(topic_id)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Téma nenalezeno.")
    return {"status": "ok"}


@app.get("/v1/function-questions", response_model=List[FunctionQuestionResponse])
async def list_function_questions() -> List[FunctionQuestionResponse]:
    rows = await DB.list_function_questions()
    return [
        FunctionQuestionResponse(
            function_question=row["function_question"],
            function=row["function"],
            text=row["text"],
        )
        for row in rows
    ]


@app.post("/v1/function-questions", response_model=FunctionQuestionResponse)
async def create_function_question(
    payload: FunctionQuestionBase,
) -> FunctionQuestionResponse:
    embedding_list = await _create_embedding(payload.text)
    embedding_value = _vector_from_list(embedding_list)
    row = await DB.create_function_question(
        payload.function,
        payload.text,
        embedding_value,
    )
    row = _ensure_row(row, "Dotaz k funkci nebyl vytvořen.")
    return FunctionQuestionResponse(
        function_question=row["function_question"],
        function=row["function"],
        text=row["text"],
    )


@app.get("/v1/function-questions/{function_question_id}", response_model=FunctionQuestionResponse)
async def get_function_question(function_question_id: int) -> FunctionQuestionResponse:
    row = await DB.get_function_question(function_question_id)
    row = _ensure_row(row, "Dotaz k funkci nenalezen.")
    return FunctionQuestionResponse(
        function_question=row["function_question"],
        function=row["function"],
        text=row["text"],
    )


@app.put("/v1/function-questions/{function_question_id}", response_model=FunctionQuestionResponse)
async def update_function_question(
    function_question_id: int,
    payload: FunctionQuestionUpdate,
) -> FunctionQuestionResponse:
    current = await DB.get_function_question(function_question_id)
    current = _ensure_row(current, "Dotaz k funkci nenalezen.")
    function_id = payload.function if payload.function is not None else current["function"]
    text_value = payload.text if payload.text is not None else current["text"]
    embedding_list = await _create_embedding(text_value)
    embedding_value = _vector_from_list(embedding_list)
    row = await DB.update_function_question(
        function_question_id,
        function_id,
        text_value,
        embedding_value,
    )
    row = _ensure_row(row, "Dotaz k funkci nebyl upraven.")
    return FunctionQuestionResponse(
        function_question=row["function_question"],
        function=row["function"],
        text=row["text"],
    )


@app.delete("/v1/function-questions/{function_question_id}")
async def delete_function_question(function_question_id: int) -> dict:
    result = await DB.delete_function_question(function_question_id)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Dotaz k funkci nenalezen.")
    return {"status": "ok"}


@app.get("/v1/functions", response_model=List[FunctionResponse])
async def list_functions() -> List[FunctionResponse]:
    rows = await DB.list_functions()
    return [
        FunctionResponse(
            function=row["function"],
            name=row["name"],
            description=row["description"],
            active=row["active"],
            type=row["type"],
            script=row["script"],
            user_roles=row["user_roles"],
            role_abbrs=row["role_abbrs"],
        )
        for row in rows
    ]


@app.post("/v1/functions", response_model=FunctionResponse)
async def create_function(payload: FunctionBase) -> FunctionResponse:
    row = await DB.create_function(
        payload.name,
        payload.description,
        payload.active,
        payload.type,
        payload.script,
    )
    row = _ensure_row(row, "Funkce nebyla vytvořena.")
    await DB.replace_function_roles(row["function"], payload.user_roles)
    updated = await DB.get_function(row["function"])
    updated = _ensure_row(updated, "Funkce nenalezena.")
    return FunctionResponse(
        function=updated["function"],
        name=updated["name"],
        description=updated["description"],
        active=updated["active"],
        type=updated["type"],
        script=updated["script"],
        user_roles=updated["user_roles"],
        role_abbrs=updated["role_abbrs"],
    )


@app.get("/v1/functions/{function_id}", response_model=FunctionResponse)
async def get_function(function_id: int) -> FunctionResponse:
    row = await DB.get_function(function_id)
    row = _ensure_row(row, "Funkce nenalezena.")
    return FunctionResponse(
        function=row["function"],
        name=row["name"],
        description=row["description"],
        active=row["active"],
        type=row["type"],
        script=row["script"],
        user_roles=row["user_roles"],
        role_abbrs=row["role_abbrs"],
    )


@app.put("/v1/functions/{function_id}", response_model=FunctionResponse)
async def update_function(function_id: int, payload: FunctionUpdate) -> FunctionResponse:
    current = await DB.get_function(function_id)
    current = _ensure_row(current, "Funkce nenalezena.")
    name = payload.name if payload.name is not None else current["name"]
    description = payload.description if payload.description is not None else current["description"]
    active = payload.active if payload.active is not None else current["active"]
    type_value = payload.type if payload.type is not None else current["type"]
    script = payload.script if payload.script is not None else current["script"]
    user_roles = payload.user_roles if payload.user_roles is not None else current["user_roles"]
    row = await DB.update_function(
        function_id,
        name,
        description,
        active,
        type_value,
        script,
    )
    row = _ensure_row(row, "Funkce nebyla upravena.")
    await DB.replace_function_roles(function_id, user_roles)
    updated = await DB.get_function(function_id)
    updated = _ensure_row(updated, "Funkce nenalezena.")
    return FunctionResponse(
        function=updated["function"],
        name=updated["name"],
        description=updated["description"],
        active=updated["active"],
        type=updated["type"],
        script=updated["script"],
        user_roles=updated["user_roles"],
        role_abbrs=updated["role_abbrs"],
    )


@app.delete("/v1/functions/{function_id}")
async def delete_function(function_id: int) -> dict:
    result = await DB.delete_function(function_id)
    if result.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="Funkce nenalezena.")
    return {"status": "ok"}


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    data = await _forward_to_llm(CHAT_BASE_URL, "/v1/models", CHAT_TIMEOUT_S, CHAT_API_KEY)
    return ModelsResponse.model_validate(data)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(payload: ChatCompletionRequest) -> ChatCompletionResponse:
    data = await _forward_to_llm(
        CHAT_BASE_URL,
        "/v1/chat/completions",
        CHAT_TIMEOUT_S,
        CHAT_API_KEY,
        payload.model_dump(),
    )
    data = _sanitize_llm_response(data)
    return ChatCompletionResponse.model_validate(data)


@app.post("/v1/embeddings")
async def create_embeddings(payload: EmbeddingRequest) -> dict:
    data = await _forward_to_llm(
        EMBEDDING_BASE_URL,
        "/v1/embeddings",
        EMBEDDING_TIMEOUT_S,
        EMBEDDING_API_KEY,
        payload.model_dump(),
    )
    return data
