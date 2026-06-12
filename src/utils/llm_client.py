import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from http.client import IncompleteRead
from typing import Any, Optional
from urllib import error, request

from .env_utils import get_env_value, load_env_file


@dataclass
class LLMConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    chat_completions_path: str = "/chat/completions"
    timeout_seconds: int = 60
    temperature: float = 0.2
    max_tokens: int = 4096


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting and retry behavior."""

    max_concurrent: int = 5
    retry_attempts: int = 3
    retry_delay_seconds: float = 2.0


def load_rate_limit_config(env_path: Optional[str] = None) -> RateLimitConfig:
    """Load rate limit configuration from environment.

    Args:
        env_path: Optional path to .env file.

    Returns:
        RateLimitConfig with values from environment or defaults.
    """
    load_env_file(env_path=env_path, override=False)

    max_concurrent = int(get_env_value("LLM_MAX_CONCURRENT", "5", env_path=env_path))
    retry_attempts = int(get_env_value("LLM_RETRY_ATTEMPTS", "3", env_path=env_path))
    retry_delay_seconds = float(get_env_value("LLM_RETRY_DELAY_SECONDS", "2.0", env_path=env_path))

    return RateLimitConfig(
        max_concurrent=max_concurrent,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )


class LLMConfigurationError(RuntimeError):
    pass


class LLMRequestError(RuntimeError):
    pass


def load_llm_config(env_path: Optional[str] = None) -> LLMConfig:
    load_env_file(env_path=env_path, override=False)

    provider = _first_non_empty(
        get_env_value("LLM_PROVIDER", env_path=env_path),
        "deepseek",
    )
    provider_upper = provider.upper()

    api_key = _require_value(
        _first_non_empty(
            os.getenv("LLM_API_KEY"),
            os.getenv(f"{provider_upper}_API_KEY"),
        ),
        message=f"Missing API key for provider '{provider}'. Set LLM_API_KEY or {provider_upper}_API_KEY.",
    )
    base_url = _require_value(
        _first_non_empty(
            os.getenv("LLM_BASE_URL"),
            os.getenv(f"{provider_upper}_BASE_URL"),
            "https://api.deepseek.com" if provider.lower() == "deepseek" else None,
        ),
        message=f"Missing base URL for provider '{provider}'.",
    ).rstrip("/")
    model = _require_value(
        _first_non_empty(
            os.getenv("LLM_MODEL"),
            os.getenv(f"{provider_upper}_MODEL"),
            "deepseek-chat" if provider.lower() == "deepseek" else None,
        ),
        message=f"Missing model for provider '{provider}'.",
    )

    chat_completions_path = _first_non_empty(
        os.getenv("LLM_CHAT_COMPLETIONS_PATH"),
        os.getenv(f"{provider_upper}_CHAT_COMPLETIONS_PATH"),
        "/chat/completions",
    )
    timeout_seconds = int(
        _first_non_empty(
            os.getenv("LLM_TIMEOUT_SECONDS"),
            os.getenv(f"{provider_upper}_TIMEOUT_SECONDS"),
            "60",
        )
    )
    temperature = float(
        _first_non_empty(
            os.getenv("LLM_TEMPERATURE"),
            os.getenv(f"{provider_upper}_TEMPERATURE"),
            "0.2",
        )
    )
    max_tokens = int(
        _first_non_empty(
            os.getenv("LLM_MAX_TOKENS"),
            os.getenv(f"{provider_upper}_MAX_TOKENS"),
            "4096",
        )
    )

    return LLMConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        chat_completions_path=chat_completions_path,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
    )


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = f"{self.config.base_url}{self.config.chat_completions_path}"
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise LLMRequestError(f"LLM HTTP error {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise LLMRequestError(f"LLM network error: {exc}") from exc
        except (IncompleteRead, TimeoutError, ConnectionResetError) as exc:
            raise LLMRequestError(f"LLM network error: {exc}") from exc

        try:
            data = json.loads(raw)
            return _extract_message_content(data)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMRequestError("Failed to parse LLM response payload.") from exc


class LLMClientWithRetry:
    """LLM client with automatic retry for rate limit errors.

    This wrapper automatically retries on 429 (rate limit) errors,
    with configurable retry attempts and delay.
    """

    def __init__(
        self,
        client: OpenAICompatibleLLMClient,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """Initialize the retry-enabled LLM client.

        Args:
            client: The underlying LLM client to wrap.
            rate_limit_config: Configuration for retry behavior. Uses defaults if None.
        """
        self._client = client
        self._config = rate_limit_config or RateLimitConfig()

    @property
    def client(self) -> OpenAICompatibleLLMClient:
        """Return the underlying LLM client."""
        return self._client

    @property
    def rate_limit_config(self) -> RateLimitConfig:
        """Return the rate limit configuration."""
        return self._config

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM with automatic retry on rate limit errors.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.

        Returns:
            LLM response content.

        Raises:
            LLMRequestError: If all retry attempts fail.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self._config.retry_attempts):
            try:
                return self._client.chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            except LLMRequestError as exc:
                error_str = str(exc).lower()
                is_rate_limit = "429" in error_str or "rate limit" in error_str
                is_transient_network = any(
                    keyword in error_str
                    for keyword in (
                        "network error",
                        "incompleteread",
                        "unexpected_eof_while_reading",
                        "eof occurred in violation of protocol",
                        "timed out",
                        "connection reset",
                    )
                )

                if (is_rate_limit or is_transient_network) and attempt < self._config.retry_attempts - 1:
                    delay = self._config.retry_delay_seconds * (attempt + 1)
                    time.sleep(delay)
                    last_error = exc
                    continue
                raise exc from last_error

        # Should not reach here, but just in case
        raise last_error or LLMRequestError("All retry attempts failed")


def build_llm_callable(
    env_path: Optional[str] = None,
    client: Optional[OpenAICompatibleLLMClient] = None,
) -> Callable[..., str]:
    base_client = client or OpenAICompatibleLLMClient(load_llm_config(env_path=env_path))
    llm_client = LLMClientWithRetry(
        base_client,
        rate_limit_config=load_rate_limit_config(env_path=env_path),
    )

    def _call_llm(*, system_prompt: str, user_prompt: str, stage: str, metadata: dict[str, Any]) -> str:
        return llm_client.chat_completion(system_prompt=system_prompt, user_prompt=user_prompt)

    return _call_llm


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload["choices"]
    message = choices[0]["message"]
    content = message["content"]

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text_parts.append(item.get("text", ""))
        return "\n".join(part for part in text_parts if part)
    raise LLMRequestError("Unsupported content format in LLM response.")


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _require_value(value: Optional[str], message: str) -> str:
    if value is None:
        raise LLMConfigurationError(message)
    return value
