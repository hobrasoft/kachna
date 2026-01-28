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

## Spuštění frontendu
```bash
cd frontend
npm install
npm run dev
```

Frontend očekává API na `http://localhost:8000`. Lze změnit přes `VITE_API_URL`.
