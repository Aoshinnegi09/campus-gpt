import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(tmp_path: Path):
    index_path = tmp_path / "index.json"

    import backend.app.config as config_module

    config_module.settings.index_path = index_path
    config_module.settings.refusal_threshold = 0.12

    import backend.app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.create_app())


def test_health(tmp_path: Path):
    client = make_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_list_and_grounded_chat(tmp_path: Path):
    client = make_client(tmp_path)

    upload = client.post(
        "/documents/upload",
        files={
            "file": (
                "policy.txt",
                b"Scholarship applications close on 15 June. Merit students can apply online.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 200

    listing = client.get("/documents")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    chat = client.post("/chat", json={"query": "When do scholarship applications close?"})
    assert chat.status_code == 200
    body = chat.json()
    assert body["grounded"] is True
    assert body["refused"] is False
    assert body["citations"]


def test_refusal_when_irrelevant_query(tmp_path: Path):
    client = make_client(tmp_path)

    client.post(
        "/documents/upload",
        files={"file": ("hostel.md", b"Hostel gate closes at 9 PM every day.", "text/markdown")},
    )
    chat = client.post("/chat", json={"query": "How to apply for a visa extension?"})
    assert chat.status_code == 200
    body = chat.json()
    assert body["refused"] is True
    assert "sufficient evidence" in body["answer"].lower()
