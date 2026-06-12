import logging
import tempfile
from pathlib import Path
from typing import Optional


def resolve_runtime_output_path(requested_path: Optional[str]) -> Optional[Path]:
    if not requested_path:
        return None

    preferred_path = Path(requested_path)
    if _is_path_writable(preferred_path):
        return preferred_path

    fallback_root = Path(tempfile.gettempdir()) / "ChaoxingAgentRuntime"
    fallback_path = fallback_root / preferred_path.as_posix().replace(":", "")
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    return fallback_path


def get_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    resolved_log_path = resolve_runtime_output_path(log_file)
    logger.runtime_log_path = str(resolved_log_path) if resolved_log_path else None

    if resolved_log_path:
        resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
        if log_file and str(resolved_log_path) != log_file:
            logger.warning(
                "Requested log path %s is not writable; falling back to %s",
                log_file,
                resolved_log_path,
            )
        file_handler = logging.FileHandler(resolved_log_path, mode="w", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def _is_path_writable(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False
