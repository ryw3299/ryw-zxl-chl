# claude_sdk/infra/agent_client.py

import asyncio
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

# 读取项目根目录或当前工作目录下的 .env
# 里面可以放 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_MODEL
load_dotenv()


class AgentClient:
    def __init__(
        self,
        name: str,
        cwd: str,
        workspace: str,
        system_prompt: str = "",
        allowed_tools: list[str] | None = None,
        permission_mode: str = "acceptEdits",
        model: str | None = None,
        mcp_servers: dict[str, Any] | None = None,
        disallowed_tools: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        self.name = name
        self.cwd = cwd
        self.workspace = Path(workspace)
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []
        self.permission_mode = permission_mode
        self.model = model
        self.mcp_servers = mcp_servers or {}
        self.disallowed_tools = disallowed_tools or []
        self.env = env or {}

        # workspace 是你自己的运行产物目录
        self.workspace.mkdir(parents=True, exist_ok=True)

        # 例如 planner -> runs/demo_client/planner.log
        self.log_path = self.workspace / f"{self.name}.log"

        # 默认输出，例如 planner -> runs/demo_client/planner_output.md
        self.default_output_path = self.workspace / f"{self.name}_output.md"

        self.client: ClaudeSDKClient | None = None
        self.started = False
        self.session_id: str | None = None

    async def start(self):
        if self.started:
            return

        options_kwargs: dict[str, Any] = {
            "cwd": self.cwd,
            "system_prompt": self.system_prompt,
            "allowed_tools": self.allowed_tools,
            "permission_mode": self.permission_mode,
            "disallowed_tools": self.disallowed_tools,
            # 关掉外部 settings.json，避免 SDK 默认配置压过我们显式传的 env / model
            "setting_sources": [],
        }

        # model 不传时，SDK 通常会读取 ANTHROPIC_MODEL 或默认配置
        # 传了就显式覆盖
        if self.model:
            options_kwargs["model"] = self.model

        if self.mcp_servers:
            options_kwargs["mcp_servers"] = self.mcp_servers

        env = dict(self.env) if self.env else {}
        # SDK 只认 ANTHROPIC_API_KEY，不认 ANTHROPIC_AUTH_TOKEN
        if "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" in env:
            env["ANTHROPIC_API_KEY"] = env["ANTHROPIC_AUTH_TOKEN"]
        if env:
            options_kwargs["env"] = env

        options = ClaudeAgentOptions(**options_kwargs)

        self.client = ClaudeSDKClient(options=options)

        # 手动打开 client 生命周期
        await self.client.__aenter__()

        self.started = True
        self._log(f"[{self.name}] started\n")

    async def ask(
        self,
        prompt: str,
        output_path: str | None = None,
        timeout: float = 600.0,
    ) -> str:
        if not self.started or self.client is None:
            raise RuntimeError(f"{self.name} is not started. Call start() first.")

        self._log(f"\n[{self.name} USER]\n{prompt}\n")

        await self.client.query(prompt)

        text_parts: list[str] = []
        raw_parts: list[str] = []

        try:
            async with asyncio.timeout(timeout):
                async for message in self.client.receive_response():
                    # log 里也保存原生 message，方便排错
                    raw = str(message)
                    raw_parts.append(raw)
                    self._log(raw + "\n\n")

                    # 有些 message 带 session_id，顺手存下来
                    maybe_session_id = getattr(message, "session_id", None)
                    if maybe_session_id:
                        self.session_id = maybe_session_id

                    # output 文件尽量保存干净文本，而不是所有原生 message
                    extracted = self._extract_text(message)
                    if extracted:
                        text_parts.append(extracted)
        except asyncio.TimeoutError:
            self._log(
                f"\n[{self.name}] TIMEOUT: No response for {timeout}s, "
                f"connection likely dropped\n"
            )
            raise

        final_text = "\n\n".join(text_parts).strip()
        if not final_text:
            final_text = "\n\n".join(raw_parts).strip()

        path = Path(output_path) if output_path else self.default_output_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(final_text, encoding="utf-8")

        return final_text

    @staticmethod
    def _is_connection_error(exc: Exception) -> bool:
        """判断是否为网络/连接类错误（需要更激进的退避）。"""
        error_msg = str(exc).lower()
        connection_keywords = (
            "connection reset", "connection refused", "broken pipe",
            "apiconnectionerror", "minimaxexception", "connectionerror",
            "ssl", "certificate", "dns", "timeout", "eof",
        )
        return any(kw in error_msg for kw in connection_keywords)

    def _compute_backoff(self, attempt: int, exc: Exception) -> float:
        """计算退避时间。连接错误用更激进的退避。"""
        if self._is_connection_error(exc):
            # 连接错误：10s, 20s, 40s, 80s, 120s...（上限 120s）
            wait = min(10 * (2 ** attempt), 120)
            self._log(
                f"\n[{self.name}] Connection error detected. "
                f"Aggressive backoff: {wait}s\n"
            )
        else:
            # 普通错误：5s, 10s, 20s, 40s, 80s...（上限 120s）
            wait = min(5 * (2 ** attempt), 120)
        return wait

    async def ask_with_retry(
        self,
        prompt: str,
        output_path: str | None = None,
        timeout: float = 600.0,
        max_retries: int = 4,
    ) -> str:
        """带重试的 ask。流式响应断线时自动重建 client 重新 ask。

        策略:
        - max_retries=4（共 5 次尝试）
        - 指数退避：5s → 10s → 20s → 40s → 80s（上限 120s）
        - 连接错误用更激进退避：10s → 20s → 40s → 80s → 120s
        - 捕获 TimeoutError + ConnectionError + OSError
        """
        last_error: Exception | None = None
        retryable_exceptions = (asyncio.TimeoutError, ConnectionError, OSError)

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self._log(
                        f"\n[{self.name}] RETRY {attempt}/{max_retries}: "
                        f"Rebuilding client...\n"
                    )
                    await self._rebuild_client()
                return await self.ask(prompt, output_path, timeout)
            except retryable_exceptions as e:
                last_error = e
                if attempt < max_retries:
                    wait = self._compute_backoff(attempt, e)
                    self._log(
                        f"\n[{self.name}] {type(e).__name__}, "
                        f"waiting {wait}s before retry {attempt + 1}/{max_retries}\n"
                    )
                    await asyncio.sleep(wait)
                else:
                    break
        raise last_error or asyncio.TimeoutError(
            f"Ask failed after {max_retries} retries"
        )

    async def _rebuild_client(self):
        """关闭旧 client 并重建新连接。"""
        try:
            await self.close(timeout=10.0)
        except Exception:
            pass
        self.client = None
        self.started = False
        await self.start()

    async def close(self, timeout: float = 30.0):
        if not self.started or self.client is None:
            return

        self._log(f"[{self.name}] closing\n")

        try:
            async with asyncio.timeout(timeout):
                await self.client.__aexit__(None, None, None)
        except asyncio.TimeoutError:
            self._log(
                f"[{self.name}] close timeout after {timeout}s, forcing cleanup\n"
            )

        self.client = None
        self.started = False

        self._log(f"[{self.name}] closed\n")

    async def kill(self):
        await self.close()

    def _log(self, text: str):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(text)

    def _extract_text(self, message) -> str:
        parts: list[str] = []

        if isinstance(message, AssistantMessage):
            for block in getattr(message, "content", []):
                if isinstance(block, TextBlock):
                    text = getattr(block, "text", "")
                    if text:
                        parts.append(text)

        elif isinstance(message, ResultMessage):
            result = getattr(message, "result", None)
            if result:
                parts.append(result)

        return "\n".join(parts).strip()
