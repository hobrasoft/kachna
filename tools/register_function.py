#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import BackendConfig
from backend.app.db import load_database


def _parse_description(output: str) -> dict[str, Any]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError("Výstup --describe není validní JSON.") from exc

    name = data.get("name")
    description = data.get("description")
    questions = data.get("questions")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Pole 'name' musí být neprázdný řetězec.")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Pole 'description' musí být neprázdný řetězec.")
    if not isinstance(questions, list) or not questions:
        raise ValueError("Pole 'questions' musí být neprázdný seznam.")
    if any(not isinstance(item, str) or not item.strip() for item in questions):
        raise ValueError("Pole 'questions' musí obsahovat neprázdné řetězce.")

    return {
        "name": name.strip(),
        "description": description.strip(),
        "questions": [item.strip() for item in questions],
    }


def _run_describe(script_path: Path) -> dict[str, Any]:
    if not script_path.is_file():
        raise FileNotFoundError(f"Skript '{script_path}' neexistuje.")
    if not script_path.is_absolute():
        script_path = script_path.resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Skript '{script_path}' neexistuje.")
    if not script_path.stat().st_mode & 0o111:
        raise PermissionError(f"Skript '{script_path}' není spustitelný.")

    result = subprocess.run(
        [str(script_path), "--describe"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Skript skončil chybou.\nSTDOUT:\n"
            f"{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return _parse_description(result.stdout)


def _embedding_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


async def _fetch_json(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if payload is None:
        response = await client.get(url, headers=_embedding_headers(BackendConfig.embeddingApiKey()))
    else:
        response = await client.post(
            url,
            json=payload,
            headers=_embedding_headers(BackendConfig.embeddingApiKey()),
        )
    response.raise_for_status()
    return response.json()


async def _get_embedding_model_id(client: httpx.AsyncClient) -> str:
    data = await _fetch_json(client, f"{BackendConfig.embeddingBaseUrl()}/v1/models")
    models = data.get("data")
    if not isinstance(models, list):
        raise RuntimeError("Embedding modely nejsou dostupné.")
    for model in models:
        if isinstance(model, dict):
            model_id = model.get("id")
            if isinstance(model_id, str) and model_id:
                return model_id
    raise RuntimeError("Embedding model nebyl nalezen.")


async def _create_embedding(client: httpx.AsyncClient, model_id: str, text: str) -> list[float]:
    payload = {"model": model_id, "input": text}
    data = await _fetch_json(client, f"{BackendConfig.embeddingBaseUrl()}/v1/embeddings", payload)
    entries = data.get("data")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("Embedding nebyl vrácen.")
    embedding = entries[0].get("embedding") if isinstance(entries[0], dict) else None
    if not isinstance(embedding, list):
        raise RuntimeError("Embedding má neplatný formát.")
    return [float(value) for value in embedding]


def _vector_from_list(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


async def _register_function(script_path: Path) -> None:
    description = _run_describe(script_path)
    script_name = script_path.name

    async with httpx.AsyncClient(timeout=BackendConfig.embeddingTimeoutSeconds()) as client:
        model_id = await _get_embedding_model_id(client)
        questions_with_embeddings: list[tuple[str, str]] = []
        for question in description["questions"]:
            embedding = await _create_embedding(client, model_id, question)
            questions_with_embeddings.append((question, _vector_from_list(embedding)))

    db = load_database()
    await db.connect()
    try:
        row = await db.upsert_function_with_questions(
            name=description["name"],
            description=description["description"],
            active=True,
            type_value="shell",
            script=script_name,
            questions=questions_with_embeddings,
        )
        roles = await db.list_roles()
        admin_role_ids = [role["user_role"] for role in roles if role["admin"]]
        await db.replace_function_roles(row["function"], admin_role_ids)
    finally:
        await db.disconnect()


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Registrace shell funkce do DB")
    parser.add_argument("script", help="Cesta ke skriptu, který podporuje --describe")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        raise FileNotFoundError(f"Skript '{script_path}' neexistuje.")

    await _register_function(script_path)


if __name__ == "__main__":
    asyncio.run(_main())
