# Kachna

Kostra projektu pro UI (React) a backend (Python FastAPI) s OpenAI-compatible API.

## Struktura
- `backend/` – FastAPI server s `/v1/models` a `/v1/chat/completions`.
- `frontend/` – React UI (Vite).

## Spuštění backendu
```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend předává OpenAI-compatible požadavky na lokální LLM.

Konfiguraci backendu lze zadat také v INI souboru (`~/.kachna.conf` nebo
`/etc/kachna.conf`). Pro chat a embedding použij:
```ini
[chat]
hostname = localhost
port = 8097
timeout = 30
api-key =

[embedding]
hostname = localhost
port = 8098
timeout = 30
api-key =
```

Pokud spouštíš server z kořene repa, můžeš použít:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Spuštění frontendu
```bash
cd frontend
npm install
npm run dev
```

Frontend očekává API na `http://localhost:8000`. Lze změnit přes `VITE_API_URL`
nebo v konfiguračním souboru (`~/.kachna.conf` nebo `/etc/kachna.conf`) pomocí
sekce `[frontend]` a klíče `api_url`.

## AI Coding Guidelines

This project uses AI-assisted code generation.

All generated or modified code MUST follow the rules defined in
[AI_INSTRUCTIONS.md](./AI_INSTRUCTIONS.md).

These rules are considered authoritative across the whole project
(frontend and backend).
