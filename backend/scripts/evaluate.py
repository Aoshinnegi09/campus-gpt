import json
from pathlib import Path

from backend.app.config import settings
from backend.app.indexing import IndexStore
from backend.app.retrieval import Retriever

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    tmp_index = BASE / "storage" / "eval_index.json"
    settings.index_path = tmp_index
    store = IndexStore(settings.index_path)

    docs = json.loads((BASE / "eval_data" / "documents.json").read_text(encoding="utf-8"))
    for doc in docs:
        store.add_document(doc["filename"], doc["content"].encode("utf-8"))

    retriever = Retriever(store)
    queries = json.loads((BASE / "eval_data" / "queries.json").read_text(encoding="utf-8"))

    k = 5
    threshold = settings.refusal_threshold
    recall_hits = 0
    answerable = 0
    refusal_correct = 0
    refusal_total = 0

    for q in queries:
        results = retriever.search(q["query"], k)
        max_score = max((r.score for r in results), default=0.0)
        predicted_refusal = max_score < threshold

        if q["should_refuse"]:
            refusal_total += 1
            if predicted_refusal:
                refusal_correct += 1
        else:
            answerable += 1
            retrieved = {r.chunk.filename for r in results}
            if q["expected_document"] in retrieved:
                recall_hits += 1

    recall_at_5 = recall_hits / answerable if answerable else 0.0
    refusal_accuracy = refusal_correct / refusal_total if refusal_total else 0.0

    print(json.dumps({"recall_at_5": round(recall_at_5, 4), "refusal_accuracy": round(refusal_accuracy, 4)}, indent=2))


if __name__ == "__main__":
    main()
