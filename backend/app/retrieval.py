from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .indexing import Chunk, IndexStore


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float


class Retriever:
    def __init__(self, store: IndexStore):
        self.store = store

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        chunks = self.store.get_chunks()
        if not chunks:
            return []

        corpus = [c.text for c in chunks]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, matrix).flatten()

        ranked_ids = scores.argsort()[::-1][:top_k]
        return [RetrievalResult(chunk=chunks[i], score=float(scores[i])) for i in ranked_ids]
