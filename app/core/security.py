import hashlib
import re
import uuid
from pathlib import Path

from app.core.exceptions import ValidationError

SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,8}$")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        while block := file_handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def generated_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    if not SAFE_EXTENSION.fullmatch(suffix):
        raise ValidationError("The uploaded filename has an invalid extension.")
    return f"{uuid.uuid4().hex}{suffix}"


def confined_path(root: Path, candidate: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    resolved = candidate.expanduser().resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValidationError("The requested path is outside local application storage.")
    return resolved


def safe_unlink(root: Path, candidate: Path) -> None:
    resolved = confined_path(root, candidate)
    if resolved.exists() and resolved.is_file():
        resolved.unlink()
