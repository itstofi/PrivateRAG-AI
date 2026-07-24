from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.core.security import confined_path, generated_filename, sha256_bytes


def test_settings_reject_overlap_equal_to_chunk() -> None:
    with pytest.raises(PydanticValidationError):
        Settings(_env_file=None, chunk_size=200, chunk_overlap=200)


def test_settings_create_runtime_directories(settings: Settings) -> None:
    settings.ensure_directories()
    assert settings.upload_dir.is_dir()
    assert settings.vector_dir.is_dir()
    assert settings.database_dir.is_dir()


def test_generated_filename_preserves_only_extension() -> None:
    stored = generated_filename("Quarterly Report.PDF")
    assert stored.endswith(".pdf")
    assert "Quarterly" not in stored
    assert len(Path(stored).stem) == 32


def test_generated_filename_rejects_missing_extension() -> None:
    with pytest.raises(ValidationError):
        generated_filename("README")


def test_sha256_is_stable() -> None:
    assert sha256_bytes(b"private") == sha256_bytes(b"private")
    assert sha256_bytes(b"private") != sha256_bytes(b"public")


def test_confined_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        confined_path(tmp_path / "uploads", tmp_path / "outside.txt")
