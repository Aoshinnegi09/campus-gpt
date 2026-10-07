import hashlib
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from .config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    filename: str
    text: str


class IndexStore:
    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write({"documents": [], "chunks": []})

    def _read(self) -> dict:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _write(self, payload: dict) -> None:
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_documents(self) -> list[dict]:
        return self._read()["documents"]

    def get_chunks(self) -> list[Chunk]:
        raw = self._read()["chunks"]
        return [Chunk(**c) for c in raw]

    def add_document(self, filename: str, content: bytes) -> tuple[str, int]:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("Only PDF, TXT, and MD files are supported")
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise ValueError(f"File too large. Max {settings.max_upload_mb}MB")

        text = extract_text(filename, content)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No extractable text found in file")

        digest = hashlib.sha256((filename + text[:500]).encode("utf-8")).hexdigest()[:12]
        document_id = f"doc_{digest}"

        data = self._read()
        data["chunks"] = [c for c in data["chunks"] if c["document_id"] != document_id]
        data["documents"] = [d for d in data["documents"] if d["document_id"] != document_id]

        raw_chunks = []
        for i, chunk in enumerate(chunks):
            raw_chunks.append(
                {
                    "chunk_id": f"{document_id}_{i}",
                    "document_id": document_id,
                    "filename": filename,
                    "text": chunk,
                }
            )

        data["documents"].append(
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_count": len(raw_chunks),
            }
        )
        data["chunks"].extend(raw_chunks)
        self._write(data)

        logger.info("Indexed document %s with %s chunks", filename, len(raw_chunks))
        return document_id, len(raw_chunks)


def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore").strip()

    reader = PdfReader(BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    size = max(settings.chunk_size_words, 20)
    overlap = min(settings.chunk_overlap_words, size - 1)
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        segment = words[start : start + size]
        if not segment:
            continue
        chunks.append(" ".join(segment))
    return chunks
