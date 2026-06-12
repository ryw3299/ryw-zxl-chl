"""Helpers for safely persisting multipart-uploaded files.

All FastAPI upload endpoints route through :func:`save_upload_file` so
the destination directory and filename normalization stays consistent.
"""

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile


def normalize_bool(value, default: bool = True) -> bool:
    """Coerce ``"true"/"false"/0/1/...`` form-field strings into ``bool``."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


async def save_upload_file(
    upload_file: UploadFile,
    target_dir: str | Path,
    *,
    preferred_suffix: Optional[str] = None,
) -> tuple[str, str, int]:
    """Persist a multipart-uploaded file under ``paths.uploads_dir``.

    Returns ``(absolute_path, original_name, byte_size)``.  The destination
    filename is randomized to prevent collisions across users.
    """
    destination_dir = Path(target_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    original_name = Path(upload_file.filename or "upload.bin").name
    suffix = preferred_suffix or Path(original_name).suffix
    if suffix and not str(suffix).startswith("."):
        suffix = f".{suffix}"

    destination_path = destination_dir / f"{uuid4().hex}{suffix or ''}"
    content = await upload_file.read()
    destination_path.write_bytes(content)

    # Closing the underlying SpooledTemporaryFile may legitimately fail if
    # the request was already torn down; we have nothing useful to do here.
    try:
        await upload_file.close()
    except (OSError, RuntimeError):
        pass

    return str(destination_path), original_name, len(content)
