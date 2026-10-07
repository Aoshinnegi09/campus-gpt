import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .indexing import IndexStore
from .qa import SAFE_REFUSAL, build_answer, maybe_generate_with_provider
from .retrieval import Retriever
from .schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    DocumentItem,
    HealthResponse,
    RetrievalMetadata,
    UploadResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("campusgpt")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = IndexStore(settings.index_path)
    retriever = Retriever(store)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/documents/upload", response_model=UploadResponse)
    async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Missing filename")

        content = await file.read()
        try:
            document_id, chunks_created = store.add_document(file.filename, content)
            return UploadResponse(document_id=document_id, filename=file.filename, chunks_created=chunks_created)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/documents", response_model=list[DocumentItem])
    async def list_documents() -> list[DocumentItem]:
        return [DocumentItem(**d) for d in store.list_documents()]

    @app.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        top_k = payload.top_k or settings.retrieval_k
        results = retriever.search(payload.query, top_k)
        max_score = max((r.score for r in results), default=0.0)

        if max_score < settings.refusal_threshold:
            return ChatResponse(
                grounded=False,
                refused=True,
                answer=SAFE_REFUSAL,
                confidence=max_score,
                citations=[],
                retrieval=RetrievalMetadata(max_score=max_score, threshold=settings.refusal_threshold, top_k=top_k),
            )

        base_answer = build_answer(payload.query, results)
        context = "\n\n".join(r.chunk.text for r in results)
        answer = await maybe_generate_with_provider(payload.query, base_answer, context)

        citations = [
            Citation(
                document_id=r.chunk.document_id,
                filename=r.chunk.filename,
                chunk_id=r.chunk.chunk_id,
                score=round(r.score, 4),
                snippet=r.chunk.text[:220],
            )
            for r in results
        ]

        return ChatResponse(
            grounded=True,
            refused=False,
            answer=answer,
            confidence=max_score,
            citations=citations,
            retrieval=RetrievalMetadata(max_score=max_score, threshold=settings.refusal_threshold, top_k=top_k),
        )

    return app


app = create_app()
