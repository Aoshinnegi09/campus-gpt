# CampusGPT

CampusGPT is a full-stack portfolio project: **FastAPI backend + React/TypeScript frontend** for grounded Q&A over uploaded campus documents.

## Features

- Health endpoint (`/health`)
- Upload PDF/TXT/MD with extension + size validation
- Text extraction + chunking
- Persistent local JSON index (`backend/storage/index.json`)
- TF-IDF lexical retrieval
- Grounded extractive answers with citations
- Safe refusal when retrieval confidence is below threshold
- Document listing endpoint
- CORS configuration
- Typed Pydantic request/response models
- Logging
- Optional OpenAI-compatible provider (env-only)
- Responsive frontend dashboard with upload/list/chat states, refusal/grounded indicators, citations, confidence and retrieval metadata
- Evaluation script with Recall@5 and refusal behavior
- Backend tests for health/upload/chat/refusal
- Docker + docker-compose local setup
- GitHub Actions CI (backend tests + frontend build)

## Monorepo structure

- `/backend` FastAPI service, tests, evaluation assets
- `/frontend` React + TypeScript Vite dashboard
- `docker-compose.yml` local orchestration
- `.github/workflows/ci.yml` CI pipeline

## Architecture

1. User uploads `.pdf`, `.txt`, or `.md`
2. Backend extracts text and chunks by configurable word windows
3. Chunks + metadata are persisted to local JSON index
4. Query runs through TF-IDF retrieval over chunks
5. If max retrieval score < threshold, assistant refuses safely
6. Else assistant returns extractive grounded answer + citations
7. Optional OpenAI-compatible provider can refine answer when env vars are set (default remains fully local/free)

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend defaults to `http://localhost:8000` API.

## API

- `GET /health` → `{ "status": "ok" }`
- `POST /documents/upload` (multipart file)
- `GET /documents` → indexed document list
- `POST /chat` body:

```json
{ "query": "When is scholarship deadline?", "top_k": 5 }
```

Response includes:

- `grounded`, `refused`
- `answer`
- `confidence`
- `citations[]`
- `retrieval` metadata (`max_score`, `threshold`, `top_k`)

## Evaluation

Run:

```bash
PYTHONPATH=. python backend/scripts/evaluate.py
```

Outputs JSON with:

- `recall_at_5`
- `refusal_accuracy`

Sample data is in:

- `backend/eval_data/documents.json`
- `backend/eval_data/queries.json`

## Tests

```bash
cd backend
PYTHONPATH=.. pytest -q
```

## Docker

```bash
docker compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:4173`

## Security notes

- No API keys are hardcoded.
- Optional provider credentials are read only from environment variables.
- Upload size and extension checks reduce abuse risks.
- Refusal behavior avoids unsupported answers when evidence is weak.

## Deployment guidance

- Deploy backend (Render/Railway/Fly.io) as Python web service.
- Deploy frontend (Vercel/Netlify) with `VITE_API_BASE_URL` set to backend URL.
- Keep `backend/storage/index.json` on persistent volume for production.

## Limitations

- Retrieval is purely lexical TF-IDF (no dense/hybrid/reranker).
- JSON file index is lightweight and not optimized for high concurrency.
- PDF extraction quality depends on source PDF text layer.
- Optional external LLM refinement is best-effort and may be skipped if provider errors.
