import logging
import re

import httpx

from .config import settings
from .retrieval import RetrievalResult

logger = logging.getLogger(__name__)

SAFE_REFUSAL = "I could not find sufficient evidence in the available documents."


def _extractive_answer(query: str, results: list[RetrievalResult]) -> str:
    if not results:
        return SAFE_REFUSAL

    q_terms = {w.lower() for w in re.findall(r"\w+", query) if len(w) > 2}
    selected: list[str] = []
    for result in results:
        sentences = re.split(r"(?<=[.!?])\s+", result.chunk.text)
        for sent in sentences:
            sent_terms = {w.lower() for w in re.findall(r"\w+", sent)}
            if q_terms & sent_terms and len(sent.strip()) > 20:
                selected.append(sent.strip())
            if len(selected) >= 3:
                break
        if len(selected) >= 3:
            break

    if not selected:
        selected = [results[0].chunk.text[:320].strip()]

    answer = " ".join(selected)
    return answer[:800]


async def maybe_generate_with_provider(query: str, answer: str, context: str) -> str:
    if not settings.openai_base_url or not settings.openai_api_key:
        return answer

    prompt = (
        "You are a grounded assistant. Use ONLY the supplied context. "
        "If context is insufficient, return exactly: "
        f"{SAFE_REFUSAL}\n\n"
        f"Question: {query}\nContext:\n{context}\n\nDraft answer:\n{answer}"
    )

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"******",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()[:1000]
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenAI-compatible provider failed: %s", exc)
        return answer


def build_answer(query: str, results: list[RetrievalResult]) -> str:
    return _extractive_answer(query, results)
