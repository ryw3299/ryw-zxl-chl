import os
from pathlib import Path
from uuid import uuid4

from src.utils.env_utils import get_env_value, load_env_file
from src.utils.llm_client import (
    LLMConfig,
    LLMRequestError,
    OpenAICompatibleLLMClient,
    build_llm_callable,
    load_llm_config,
)


def test_env_utils_loads_values_from_env_file():
    env_path = _create_workspace_env_file(
        [
            "LLM_PROVIDER=deepseek",
            "LLM_API_KEY=test_key",
            "LLM_BASE_URL=https://api.deepseek.com",
            "LLM_MODEL=deepseek-chat",
        ]
    )
    try:
        loaded = load_env_file(str(env_path), override=True)

        assert loaded["LLM_API_KEY"] == "test_key"
        assert get_env_value("LLM_MODEL", env_path=str(env_path)) == "deepseek-chat"
    finally:
        env_path.unlink(missing_ok=True)


def test_load_llm_config_reads_openai_compatible_settings():
    keys = [
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_CHAT_COMPLETIONS_PATH",
        "LLM_TIMEOUT_SECONDS",
        "LLM_TEMPERATURE",
        "LLM_MAX_TOKENS",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_CHAT_COMPLETIONS_PATH",
        "DEEPSEEK_TIMEOUT_SECONDS",
        "DEEPSEEK_TEMPERATURE",
        "DEEPSEEK_MAX_TOKENS",
    ]
    previous_env = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)

    env_path = _create_workspace_env_file(
        [
            "LLM_PROVIDER=deepseek",
            "LLM_API_KEY=test_key",
            "LLM_BASE_URL=https://api.deepseek.com",
            "LLM_MODEL=deepseek-chat",
            "LLM_CHAT_COMPLETIONS_PATH=/chat/completions",
            "LLM_TIMEOUT_SECONDS=30",
            "LLM_TEMPERATURE=0.1",
            "LLM_MAX_TOKENS=2048",
        ]
    )
    try:
        config = load_llm_config(str(env_path))

        assert config.provider == "deepseek"
        assert config.api_key == "test_key"
        assert config.base_url == "https://api.deepseek.com"
        assert config.model == "deepseek-chat"
        assert config.chat_completions_path == "/chat/completions"
        assert config.timeout_seconds == 30
        assert config.temperature == 0.1
        assert config.max_tokens == 2048
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        env_path.unlink(missing_ok=True)


def test_build_llm_callable_uses_injected_client():
    class FakeClient(OpenAICompatibleLLMClient):
        def __init__(self):
            super().__init__(
                LLMConfig(
                    provider="deepseek",
                    api_key="unused",
                    base_url="https://api.deepseek.com",
                    model="deepseek-chat",
                )
            )

        def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
            return '{"lesson_summary":"ok","pages":[],"sections":[],"knowledge_points":[]}'

    llm_callable = build_llm_callable(client=FakeClient())
    response = llm_callable(
        system_prompt="system",
        user_prompt="user",
        stage="single_pass",
        metadata={},
    )

    assert "lesson_summary" in response


def test_build_llm_callable_retries_transient_network_errors():
    class FlakyClient(OpenAICompatibleLLMClient):
        def __init__(self):
            super().__init__(
                LLMConfig(
                    provider="deepseek",
                    api_key="unused",
                    base_url="https://api.deepseek.com",
                    model="deepseek-chat",
                )
            )
            self.calls = 0

        def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
            self.calls += 1
            if self.calls == 1:
                raise LLMRequestError("LLM network error: IncompleteRead(0 bytes read)")
            return '{"lesson_summary":"ok","pages":[],"sections":[],"knowledge_points":[]}'

    flaky_client = FlakyClient()
    llm_callable = build_llm_callable(client=flaky_client)
    response = llm_callable(
        system_prompt="system",
        user_prompt="user",
        stage="single_pass",
        metadata={},
    )

    assert flaky_client.calls == 2
    assert "lesson_summary" in response


def _create_workspace_env_file(lines: list[str]) -> Path:
    generated_dir = Path(__file__).resolve().parents[1] / "fixtures" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    env_path = generated_dir / f"test_llm_{uuid4().hex}.env"
    env_path.write_text("\n".join(lines), encoding="utf-8")
    return env_path
