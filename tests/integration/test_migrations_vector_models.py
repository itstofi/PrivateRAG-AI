from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.rag.vector_store import VectorStore
from app.storage import database


def test_database_initialization_applies_migrations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "migrated.db"
    settings = Settings(
        _env_file=None,
        app_env="test",
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{database_path}",
    )
    engine = create_engine(settings.database_url)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "get_settings", lambda: settings)
    database.init_database()
    inspector = inspect(engine)
    assert "embedding_model" in {column["name"] for column in inspector.get_columns("documents")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == (
            "0002"
        )


def test_embedding_models_use_separate_collections_and_global_deletion(
    tmp_path: Path,
) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        ollama_embedding_model="embed-a",
    )
    settings.ensure_directories()
    store = VectorStore(settings)
    metadata = {
        "workspace_id": "workspace",
        "document_id": "document",
        "source_filename": "policy.txt",
        "chunk_number": 1,
    }
    store.add(["a"], ["alpha"], [[1.0, 0.0]], [metadata])
    settings.ollama_embedding_model = "embed-b"
    store.add(["b"], ["beta"], [[1.0, 0.0, 0.0]], [metadata])
    assert store.count() == 1
    assert store.total_count() == 2
    store.delete_document("document")
    assert store.total_count() == 0
