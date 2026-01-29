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
export LLM_BASE_URL=http://localhost:8098
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend předává OpenAI-compatible požadavky na lokální LLM přes `LLM_BASE_URL`
(default `http://localhost:8098`). Volitelně lze nastavit `LLM_TIMEOUT_S` a
`LLM_API_KEY`.

Konfiguraci backendu lze zadat také v INI souboru (`~/.kachna.conf` nebo
`/etc/kachna.conf`).

## Spuštění frontendu
```bash
cd frontend
npm install
npm run dev
```

Frontend očekává API na `http://localhost:8000`. Lze změnit přes `VITE_API_URL`
nebo v konfiguračním souboru (`~/.kachna.conf` nebo `/etc/kachna.conf`) pomocí
sekce `[frontend]` a klíče `api_url`.
