# claude_sdk/infra/agent_factory.py

from pathlib import Path
from typing import Any

import yaml

from claude_sdk.infra.agent_client import AgentClient
from claude_sdk.infra.providers import load_provider_env
from claude_sdk.tools.registry import build_mcp_servers


class AgentFactory:
    """
    静态 Agent 工厂。

    当前设计：
    - agent_name 决定读取 prompts/{agent_name}.yaml
    - skills 参数决定读取 skills/{skill}.yaml
    - tools 参数决定 Claude allowed_tools
    - custom_tools 参数决定要注入哪些自定义 MCP 工具
    - provider / env_file 参数决定从 providers/<name>.env 加载哪个供应商配置
    - prompt + skills 最终拼成 system_prompt

    prompt yaml 支持两种格式：
    - 简单格式：role / instructions / output_format 三段
    - 多段格式：顶层 `sections: [...]` 指定要拼接的 section key 列表
    """

    @staticmethod
    def create_agent(
        agent_name: str,
        cwd: str,
        workspace: str,
        skills: list[str] | None = None,
        tools: list[str] | None = None,
        project_root: str | Path | None = None,
        permission_mode: str = "acceptEdits",
        model: str | None = None,
        custom_tools: list[str] | None = None,
        disallowed_tools: list[str] | None = None,
        env: dict[str, str] | None = None,
        provider: str | None = None,
        env_file: str | None = None,
    ) -> AgentClient:
        root = AgentFactory._resolve_project_root(project_root)

        prompt_config = AgentFactory._load_agent_prompt(
            root=root,
            agent_name=agent_name,
        )

        system_prompt = AgentFactory._build_system_prompt(
            root=root,
            prompt_config=prompt_config,
            skills=skills or [],
        )

        mcp_servers, custom_allowed_tools = build_mcp_servers(custom_tools)

        allowed_tools = list(tools or [])
        allowed_tools.extend(custom_allowed_tools)

        # Provider env resolution.
        # Resolution order:
        #   1. explicit env_file > providers/<provider>.env > (nothing)
        #   2. explicit env dict always overrides provider entries
        # If `model` is not explicitly given, fall back to provider's ANTHROPIC_MODEL.
        provider_env = load_provider_env(
            provider=provider,
            env_file=env_file,
            project_root=root,
        )
        merged_env: dict[str, str] = {**provider_env, **(env or {})}
        resolved_model = model or provider_env.get("ANTHROPIC_MODEL")

        return AgentClient(
            name=prompt_config.get("name", agent_name),
            cwd=cwd,
            workspace=workspace,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            model=resolved_model,
            mcp_servers=mcp_servers,
            disallowed_tools=disallowed_tools,
            env=merged_env or None,
        )

    @staticmethod
    def _resolve_project_root(project_root: str | Path | None) -> Path:
        if project_root is not None:
            return Path(project_root).resolve()

        return Path.cwd().resolve()

    @staticmethod
    def _load_agent_prompt(root: Path, agent_name: str) -> dict[str, Any]:
        path = root / "prompts" / f"{agent_name}.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Agent prompt config not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid agent prompt yaml: {path}")

        return data

    @staticmethod
    def _load_skill(root: Path, skill_name: str) -> str:
        path = root / "skills" / f"{skill_name}.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Skill config not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid skill yaml: {path}")

        content = data.get("content", "")

        if not content:
            raise ValueError(f"Skill '{skill_name}' has empty content: {path}")

        return content.strip()

    @staticmethod
    def _build_system_prompt(
        root: Path,
        prompt_config: dict[str, Any],
        skills: list[str],
    ) -> str:
        # 多段格式优先（顶层带 `sections: [...]`）
        if "sections" in prompt_config:
            return AgentFactory._build_system_prompt_from_sections(
                root, prompt_config, skills
            )

        # 简单格式：role / instructions / output_format
        parts: list[str] = []

        role = prompt_config.get("role", "")
        instructions = prompt_config.get("instructions", "")
        output_format = prompt_config.get("output_format", "")

        if role:
            parts.append("# Role\n" + role.strip())

        if instructions:
            parts.append("# Instructions\n" + instructions.strip())

        if skills:
            skill_contents = [
                AgentFactory._load_skill(root, skill_name)
                for skill_name in skills
            ]
            parts.append("# Skills\n" + "\n\n".join(skill_contents))

        if output_format:
            parts.append("# Output Format\n" + output_format.strip())

        return "\n\n".join(parts)

    @staticmethod
    def _build_system_prompt_from_sections(
        root: Path,
        prompt_config: dict[str, Any],
        skills: list[str],
    ) -> str:
        """多段 prompt 拼接。

        prompt yaml 例：
            name: explorer
            sections:
              - system_prompt
              - critical_tool_usage
              - exploration_strategy
            system_prompt: |
              ...
            critical_tool_usage: |
              ...
            exploration_strategy: |
              ...

        拼接顺序由 `sections` 列表决定。每个 section 用 `## <Title>` 作为标题，
        skills 内容追加在最后。
        """
        sections = prompt_config.get("sections", [])
        if not sections:
            # 没有任何 section 时回退到简单格式
            return AgentFactory._build_system_prompt(root, prompt_config, skills)

        parts: list[str] = []

        name = prompt_config.get("name", "")
        if name:
            parts.append(f"# Agent: {name}\n")

        for section_key in sections:
            if section_key in prompt_config:
                content = prompt_config[section_key]
                if content:
                    header = section_key.replace("_", " ").title()
                    parts.append(f"## {header}\n\n{str(content).strip()}")

        if skills:
            skill_contents = [
                AgentFactory._load_skill(root, skill_name)
                for skill_name in skills
            ]
            parts.append("# Skills\n" + "\n\n".join(skill_contents))

        return "\n\n".join(parts)
