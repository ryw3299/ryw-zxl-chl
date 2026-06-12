# Claude SDK 适配文档

> 本文档记录将 ClaudeTemplate（Claude Agent SDK）引入 ChaoXingAgent 作为非侵入式替代 OpenHands 学生问答 Agent 的全部改动。
> 更新日期：2026-05-11

---

## 一、总体设计目标

1. **非侵入式**：不改动原有 OpenHands 学生链路的一行代码（`agent.py`、`response_builder.py`、Service 层、Router 层、DB Schema 均保持原样）。
2. **可切换**：通过环境变量 `STUDENT_AGENT_BACKEND` 在 OpenHands 与 Claude SDK 之间切换，默认仍为 OpenHands。
3. **签名兼容**：`run_student_agent()` 与 `build_student_agent_turn()` 的输入输出签名与原版完全一致，上层调用方零感知。
4. **基础设施复用**：将 ClaudeTemplate 的 `infra/`、`prompts/`、`skills/`、`providers/`、`tools/` 完整迁移到 ChaoXingAgent 根目录的 `claude_sdk/` 命名空间下。

---

## 二、目录结构变更

### 2.1 新增目录与文件

```
ChaoxingAgent/
├── claude_sdk/                          # 新增：Claude SDK 基础设施命名空间
│   ├── __init__.py                      # 空包标记
│   ├── infra/
│   │   ├── __init__.py                  # 导出 AgentClient、AgentFactory、load_provider_env
│   │   ├── agent_client.py              # AgentClient：包装 ClaudeSDKClient，提供 start/ask/ask_with_retry/close
│   │   ├── agent_factory.py             # AgentFactory：从 YAML prompt + skill + provider 配置组装 AgentClient
│   │   └── providers.py                 # Provider env 加载器，支持 ${VAR} 变量引用
│   ├── prompts/
│   │   └── student_qa.yaml              # 学生问答 Agent 的 system prompt（role / instructions / output_format）
│   ├── skills/
│   │   └── student_qa.yaml              # 学生问答 Skill（按问题类型定义教学风格规范）
│   ├── providers/
│   │   └── minimax.env                  # Minimax provider 映射：ANTHROPIC_BASE_URL=${MINIMAX_BASE_URL}
│   └── tools/
│       ├── __init__.py                  # 空包标记
│       └── registry.py                  # MCP Tool 注册表（当前为空，预留扩展）
│
└── src/agents/student/
    └── claude_runner.py                 # 新增：Claude SDK 学生问答 Agent 适配层
```

### 2.2 修改的文件（仅 1 个）

```
src/agents/student/__init__.py           # 增加环境变量切换逻辑，默认仍走 OpenHands
```

### 2.3 完全未改动的原有文件

```
src/agents/student/agent.py              # OpenHands Agent 主逻辑（完整保留）
src/agents/student/response_builder.py   # 收口层（新旧路径共用）
src/agents/__init__.py                   # 上层导入（不变）
src/api/services/qa_service.py           # Service 编排层（不变）
src/api/routers/qa.py                    # HTTP Router（不变）
src/services/student/context_builder.py  # 预 RAG 上下文组装（不变）
src/services/student/retrieval_service.py # RAG 检索（不变）
src/services/student/session_service.py  # Session 状态管理（不变）
src/services/student/conversation_service.py # 对话历史（不变）
```

---

## 三、各新增文件详细说明

### 3.1 claude_sdk/infra/agent_client.py

**职责**：包装 `claude_agent_sdk.ClaudeSDKClient`，提供生命周期管理和重试机制。

**核心方法**：
- `async start()`：创建 `ClaudeAgentOptions` 并初始化 `ClaudeSDKClient`，打开连接。
- `async ask(prompt, timeout)`：发送 user message，流式接收响应，聚合文本后返回。
- `async ask_with_retry(prompt, timeout, max_retries=4)`：带指数退避（5s→10s→20s→40s→80s）的重试 ask；连接错误使用更激进退避（10s 起步）。失败自动重建 client。
- `async close()`：优雅关闭连接。

**注意**：每次提问都会新建并销毁 AgentClient（与原有 OpenHands 路径行为一致）。

### 3.2 claude_sdk/infra/agent_factory.py

**职责**：静态工厂，从配置文件组装 AgentClient。

**输入参数**：
- `agent_name`：决定读取 `claude_sdk/prompts/{agent_name}.yaml`
- `skills`：决定读取 `claude_sdk/skills/{skill}.yaml`
- `provider`：决定读取 `claude_sdk/providers/{provider}.env`
- `model`：显式覆盖 provider 中的模型配置

**system_prompt 拼接规则**：
```
# Role          (来自 prompt yaml)
# Instructions  (来自 prompt yaml)
# Output Format (来自 prompt yaml)
# Skills        (来自 skill yaml，追加在最后)
```

**provider 解析规则**：
- `providers/minimax.env` 中 `${MINIMAX_BASE_URL}` 等变量从项目根 `.env` 解析。
- 支持 `ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_MODEL` 等 Claude SDK 所需键。

### 3.3 claude_sdk/infra/providers.py

**职责**：`.env` 文件加载与 `${VAR}` 变量引用解析。

- `load_dotenv()` 在 import 时自动执行，加载项目根 `.env`。
- `_expand_env_refs()` 解析 `${VAR}` 和 `$VAR` 格式，未定义的变量保留字面量并打印 warning。
- 加载顺序：`env_file` 参数 > `providers/<provider>.env` > 空 dict。

### 3.4 claude_sdk/prompts/student_qa.yaml

**职责**：定义学生问答 Agent 的 system prompt。

**三段式结构**：
- `role`：你是课程学习平台的 AI 教学助手。
- `instructions`：
  - 用中文回答
  - 严格基于检索上下文，不编造
  - 不说"根据检索结果"等元评论
  - 简洁（2-4 句话直接回答，推理用一小段）
  - 闲聊友好回应，无上下文时诚实告知
- `output_format`：强制 JSON 输出，包含四个字段：
  - `answer`：给学生看的中文答案
  - `understanding_level`：`full|partial|none|null`
  - `next_action`：`resume|supplement_then_resume|reteach_slowly|trigger_game`
  - `reason`：选择 next_action 的中文理由（20-50 字）

### 3.5 claude_sdk/skills/student_qa.yaml

**职责**：按问题类型定义教学风格规范，拼接到 system prompt 的 `# Skills` 区块。

**覆盖类型**：
- `definition`：一句话精确定义 + 一句话说明重要性/应用
- `reasoning`：先说结论，再展开因果链条
- `procedure`：按步骤列出，每步给目的说明
- `example`：给贴合课件的例子，指出核心知识点
- `comparison`：对比表格或并列句式
- `summary`：提炼 2-3 个要点，清单形式
- `chitchat`：友好回应，自然引导回课程内容
- `unknown`：澄清意图后再尝试回答

### 3.6 claude_sdk/providers/minimax.env

**内容**：
```
ANTHROPIC_BASE_URL=${MINIMAX_BASE_URL}
ANTHROPIC_AUTH_TOKEN=${MINIMAX_API_KEY}
ANTHROPIC_MODEL=${MINIMAX_MODEL}
ANTHROPIC_SMALL_FAST_MODEL=${MINIMAX_MODEL}
ANTHROPIC_DEFAULT_SONNET_MODEL=${MINIMAX_MODEL}
ANTHROPIC_DEFAULT_OPUS_MODEL=${MINIMAX_MODEL}
API_TIMEOUT_MS=${API_TIMEOUT_MS}
```

**说明**：
- `ANTHROPIC_*` 前缀是为了兼容 Claude SDK 的环境变量读取机制。
- 实际值从项目根 `.env` 的 `MINIMAX_BASE_URL`、`MINIMAX_API_KEY`、`MINIMAX_MODEL` 解析。
- 如需新增 provider（如阿里云、讯飞等），在 `claude_sdk/providers/` 下新建 `.env` 文件即可。

### 3.7 claude_sdk/tools/registry.py

**职责**：MCP Tool 注册表。

- 当前 `TOOL_REGISTRY` 为空字典，学生问答场景不需要自定义 MCP 工具（RAG 由后端预做）。
- 预留扩展：如需让 Claude Agent 调用 game 工具生成互动测验，可在此注册。

### 3.8 src/agents/student/claude_runner.py

**职责**：Claude SDK 路径的完整执行逻辑，替换原有的 OpenHands Agent 事件循环。

**入口函数**（签名与原版一致）：
```python
def run_student_agent(request, *, llm=None) -> dict

def build_student_agent_turn(request, *, llm=None) -> dict
```

**内部流程**：
1. 校验 `StudentAgentRequest`，提取 `turn_context`（后端预组装）。
2. `asyncio.run(_run_claude_turn(request, ctx))`：
   - `AgentFactory.create_agent()` 实例化 `AgentClient`
   - `agent.start()` 建立连接
   - `agent.ask_with_retry(prompt)` 发送上下文 prompt，接收 LLM 输出
   - `agent.close()` 关闭连接
3. `_parse_claude_response()`：
   - `_extract_json_dict()` 三层清洗（去 markdown 标记 → 直接 parse → 正则提取第一个 `{...}`）
   - 解析为 `qa_output` + `decision_output` 两个 dict
   - JSON 解析失败时 fallback：用课时 summary 生成答案 + `next_action="resume"`
4. `build_student_agent_response()`（复用原有收口层）组装 `StudentAgentResponse`
5. 返回与 OpenHands 路径完全一致的 dict 结构（含 `output`、`qa_output`、`decision_output`、`tool_trace`、`events`）

**Prompt 构建**：`_build_context_turn_prompt()`
- 把 `exact_source`（精读内容）+ `retrieved_chunks[:3]`（参考内容）+ `recent_turns[-3:]`（历史对话）拼成 user message。
- 要求 LLM 基于检索上下文直接输出 JSON。

---

## 四、修改的文件详细说明

### 4.1 src/agents/student/__init__.py

**改动前**：
```python
from .agent import build_student_agent_turn, run_student_agent

__all__ = ["build_student_agent_turn", "run_student_agent"]
```

**改动后**：
```python
import os

if os.getenv("STUDENT_AGENT_BACKEND", "openhands").lower() == "claude":
    from .claude_runner import build_student_agent_turn, run_student_agent
else:
    from .agent import build_student_agent_turn, run_student_agent

__all__ = ["build_student_agent_turn", "run_student_agent"]
```

**说明**：Python import 是执行时条件判断，只会加载一种 backend 的代码到内存中，不存在代码冲突或残留。

---

## 五、使用方式

### 5.1 环境要求

```bash
# 确保 claude_agent_sdk 已安装
pip install claude-agent-sdk  # 或 claude_agent_sdk（以实际包名为准）
```

### 5.2 配置 .env

在项目根 `.env` 中补充（基于已有的 Minimax 配置）：
```
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_API_KEY=sk-...
MINIMAX_MODEL=MiniMax-M2.7
```

可选配置：
```
CLAUDE_PROVIDER=minimax          # 选择 provider，默认 minimax
CLAUDE_MODEL=MiniMax-M2.7        # 显式覆盖模型（优先级高于 provider env）
CLAUDE_ASK_TIMEOUT=60.0          # 单次 ask 超时（秒），默认 60
STUDENT_AGENT_BACKEND=claude     # 切换 backend，默认 openhands
```

### 5.3 启动服务（切换 backend）

**方式一：环境变量**
```bash
export STUDENT_AGENT_BACKEND=claude
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

**方式二：Python 代码（不推荐，仅用于测试）**
```python
import os
os.environ["STUDENT_AGENT_BACKEND"] = "claude"
```

**恢复 OpenHands（默认）**：
```bash
# 不设置 STUDENT_AGENT_BACKEND，或显式设为 openhands
export STUDENT_AGENT_BACKEND=openhands
```

---

## 六、设计决策与注意事项

### 6.1 为什么把 ClaudeTemplate 放在根目录而不是 src/ 下？

- `claude_sdk/` 是一套独立的基础设施，不依赖 `src/` 内的任何业务代码（除了 `claude_runner.py` 反向 import）。
- 放在根目录便于管理 prompt/skill/provider 配置，与 `src/` 内的业务逻辑物理隔离。

### 6.2 为什么 `AgentFactory._resolve_project_root` 指向 `claude_sdk/` 而不是项目根？

- `AgentFactory` 需要读取 `prompts/`、`skills/`、`providers/` 目录。
- 在 ChaoXingAgent 中这些目录位于 `claude_sdk/` 下，所以 `project_root` 需要指向 `claude_sdk/`。
- `claude_runner.py` 中通过 `_resolve_claude_sdk_root()` 计算该路径。

### 6.3 为什么 `claude_runner.py` 里要 `asyncio.run()` 包一层？

- `qa_service.run_qa_interact()` 是 sync 函数（FastAPI `def` 路由内部调用）。
- Claude SDK 的 `ask()` 是 async 的，需要事件循环。
- OpenHands 原有路径内部也使用 `anyio.run()` 包 async，所以行为一致。

### 6.4 为什么每次提问都新建 AgentClient？

- 与 OpenHands 原有路径行为一致（每轮新建 `Conversation` 和 Agent）。
- FastAPI sync 路由调用 `asyncio.run()`，无法跨调用复用异步连接。
- 如需优化，需将 Service 层和 Router 层改为 `async def` + 应用级 Agent 连接池，但这属于侵入式改动，当前阶段不做。

### 6.5 关于 JSON 解析的脏数据处理

- Claude SDK 协议层是干净的（`TextBlock.text` 是纯文本）。
- 但 LLM 模型输出可能带 markdown 代码块标记（```json ... ```）或前后废话。
- `claude_runner.py` 的 `_extract_json_dict()` 提供三层清洗：去 markdown → 直接 parse → 正则提取第一个 `{...}`。
- 解析失败时 fallback 到课时 summary + 默认 action，系统不会崩溃。
- 如实际测试发现 JSON 失败率偏高，可：
  1. 优化 prompt 强调"不要 markdown 代码块"
  2. 在 Claude SDK 层面使用 `response_format={"type": "json_object"}`（如果 provider 支持）

### 6.6 关于与 OpenHands 的冲突

- `claude_runner.py` 没有 import 任何 OpenHands 模块。
- 切换逻辑在 `__init__.py` 中通过环境变量条件 import 实现，两种 backend 不会同时加载到内存。
- 共享代码只有 Pydantic Schema 定义（`StudentAgentRequest`、`StudentTurnContext` 等）和 `response_builder.py`（纯文本工具函数，无 OpenHands 依赖）。

---

## 七、验证清单

- [ ] 安装 `claude_agent_sdk` 包
- [ ] 确认 `.env` 中包含 `MINIMAX_BASE_URL`、`MINIMAX_API_KEY`、`MINIMAX_MODEL`
- [ ] 设置 `STUDENT_AGENT_BACKEND=claude` 启动服务
- [ ] 调用 `/api/v1/qa/interact` 接口，确认返回正常
- [ ] 检查日志目录 `data/student_qa_runs/{session_id}/` 是否有 agent 日志
- [ ] 取消环境变量（默认 openhands），确认原 OpenHands 路径仍正常工作
