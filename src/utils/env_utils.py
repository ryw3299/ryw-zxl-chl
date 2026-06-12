import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None, override: bool = False) -> dict[str, str]:
    resolved_path = Path(env_path) if env_path else Path.cwd() / ".env"
    if not resolved_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in resolved_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_wrapping_quotes(value.strip())
        loaded[key] = value

        if override or key not in os.environ:
            os.environ[key] = value

    return loaded


def get_env_value(
    key: str,
    default: Optional[str] = None,
    env_path: Optional[str] = None,
    auto_load: bool = True,
) -> Optional[str]:
    if auto_load:
        load_env_file(env_path=env_path, override=False)
    return os.getenv(key, default)


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
