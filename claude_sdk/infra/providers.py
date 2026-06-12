# claude_sdk/infra/providers.py

"""Provider env loader with ${VAR} expansion.

Design:
- The single source of truth for secrets is the project-root `.env`.
- `providers/<name>.env` is a thin profile that maps ANTHROPIC_* keys to
  whichever provider-prefixed vars from `.env` you want to use, via
  `${VAR_NAME}` references.

Adding a new provider:
1. Append the provider's secret block to `.env`, e.g.:
       QWEN_BASE_URL=https://...
       QWEN_AUTH_TOKEN=sk-...
       QWEN_MODEL=qwen-coder-plus
2. Create `providers/qwen.env`:
       ANTHROPIC_BASE_URL=${QWEN_BASE_URL}
       ANTHROPIC_AUTH_TOKEN=${QWEN_AUTH_TOKEN}
       ANTHROPIC_MODEL=${QWEN_MODEL}
       ...
3. Use it: `AgentFactory.create_agent(provider="qwen", ...)`.

Profile selection precedence inside AgentFactory:
    explicit env > resolved provider env > (nothing)
"""

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("providers")

# Ensure `.env` is loaded at import time so ${VAR} expansion can see it.
# Use explicit project-root path so loading works regardless of CWD.
_project_root = Path(__file__).resolve().parents[2]
_dotenv_path = _project_root / ".env"
if _dotenv_path.exists():
    load_dotenv(dotenv_path=str(_dotenv_path), override=True)
    logger.info("Loaded .env from %s", _dotenv_path)
else:
    load_dotenv()  # fallback to default find_dotenv behavior
    logger.warning(".env not found at %s, falling back to find_dotenv()", _dotenv_path)


# `${VAR}` 优先匹配；其次 `$VAR`（要求后面跟字母/数字/下划线）
_VAR_PATTERN = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}"
    r"|\$([A-Za-z_][A-Za-z0-9_]*)"
)


def _expand_env_refs(value: str, source: str) -> str:
    """Expand `${VAR}` / `$VAR` references using os.environ.

    Unresolved references are kept as the literal `${VAR}` token and a warning
    is logged, so a missing var fails loudly later rather than silently.
    """
    if not value:
        return value

    def _sub(match: "re.Match[str]") -> str:
        name = match.group(1) or match.group(2)
        if name in os.environ:
            return os.environ[name]
        logger.warning(
            f"{source}: variable ${{{name}}} not found in environment, "
            f"keeping literal"
        )
        return match.group(0)

    return _VAR_PATTERN.sub(_sub, value)


def load_provider_env(
    provider: str | None = None,
    env_file: str | None = None,
    project_root: str | Path | None = None,
) -> dict[str, str]:
    """Resolve provider env vars from a named profile or an explicit file.

    Resolution order:
      1. `env_file` if given and exists — wins outright.
      2. `<project_root>/providers/<provider>.env` if provider is given.
      3. Empty dict if neither resolves.

    Each KEY=VALUE line has `${VAR}` / `$VAR` references expanded against
    the current `os.environ` (which has the project `.env` loaded).
    """
    env_path: Path | None = None

    if env_file:
        candidate = Path(env_file)
        if candidate.exists():
            env_path = candidate
        else:
            logger.warning(f"env_file not found: {candidate}")
    elif provider:
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        candidate = root / "providers" / f"{provider}.env"
        if candidate.exists():
            env_path = candidate
        else:
            logger.warning(f"Provider config not found: {candidate}")

    provider_env: dict[str, str] = {}
    if env_path is None:
        return provider_env

    logger.info(f"Loading provider env: {env_path}")
    source_label = env_path.name

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Strip matching surrounding quotes, like dotenv does.
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            provider_env[key] = _expand_env_refs(val, source_label)

    logger.info(
        f"Loaded {len(provider_env)} env vars from {source_label} "
        f"(with ${{VAR}} expansion)"
    )
    return provider_env
