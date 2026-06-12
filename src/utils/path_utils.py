import os
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from src.schemas import FileType

SUPPORTED_INPUT_TYPES = {
    "pdf",
    "ppt",
    "pptx",
    "docx",
    "txt",
    "md",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "image",
}


def strip_wrapping_quotes(value: str) -> str:
    normalized = (value or "").strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        return normalized[1:-1].strip()
    return normalized.strip('"').strip("'")


def normalize_local_path(raw_path: str) -> str:
    normalized = strip_wrapping_quotes(raw_path)
    normalized = os.path.expandvars(normalized)
    normalized = os.path.expanduser(normalized)
    return normalized


def parse_asset_input_spec(raw_spec: str) -> tuple[str, Optional[FileType]]:
    normalized = (raw_spec or "").strip()
    if not normalized:
        raise ValueError("Asset input is empty.")

    explicit_type: Optional[FileType] = None
    path_part = normalized

    if "|" in normalized:
        candidate_path, candidate_type = normalized.rsplit("|", 1)
        candidate_type = candidate_type.strip().lower()
        if candidate_type in SUPPORTED_INPUT_TYPES:
            path_part = candidate_path
            explicit_type = candidate_type  # type: ignore[assignment]

    return normalize_local_path(path_part), explicit_type


def parse_asset_input_lines(raw_lines: Sequence[str]) -> list[tuple[str, Optional[FileType]]]:
    parsed: list[tuple[str, Optional[FileType]]] = []
    for raw_line in raw_lines:
        line = (raw_line or "").strip()
        if not line:
            continue
        parsed.append(parse_asset_input_spec(line))
    return parsed


def ensure_existing_file(path_value: str) -> Path:
    if not path_value:
        raise ValueError("File path is empty.")

    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path_value}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path_value}")
    return path.resolve()
