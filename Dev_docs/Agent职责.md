# Agent 职责

## Student Architect Agent

- 负责: 维护 `Dev_docs`，冻结结构、contract、树和关键签名，审查 worker 结果并做最终集成判定
- 不负责: 大面积底层实现替代 worker 完成
- 优先阅读:
  - `Dev_docs/PROJECT_BRIEF.md`
  - `Dev_docs/FLOW.md`
  - `Dev_docs/CONTRACT.md`
  - `Dev_docs/TREE_AND_ANCHOR.md`

## Memory Agent

- 负责:
  - `src/memory/__init__.py`
  - `src/memory/session_store.py`
  - `src/memory/history.py`
  - `src/memory/condenser.py`
  - `tests/student/test_memory.py`
- 不负责:
  - `src/agents/student/*`
  - `src/utils/student/*`
  - `src/schemas/*`
- 优先阅读:
  - `Dev_docs/CONTRACT.md`
  - `Dev_docs/TREE_AND_ANCHOR.md`
  - `docs/student_contract.md`

## Retrieval Agent

- 负责:
  - `src/utils/student/__init__.py`
  - `src/utils/student/embedder.py`
  - `src/utils/student/vector_store.py`
  - `src/utils/student/hybrid_retriever.py`
  - `src/utils/student/content_getter.py`
  - `src/utils/student/helpers.py`
  - `src/utils/student/constants.py`
  - `tests/student/test_retrieval_utils.py`
- 不负责:
  - `src/agents/student/*`
  - `src/memory/*`
  - `src/schemas/*`
- 优先阅读:
  - `Dev_docs/FLOW.md`
  - `Dev_docs/CONTRACT.md`
  - `docs/student_contract.md`

## Skills Agent

- 负责:
  - `src/skills/__init__.py`
  - `src/skills/*/SKILL.md`
- 不负责:
  - `src/agents/student/*`
  - `src/memory/*`
  - `src/utils/student/*`
  - `src/schemas/*`
- 优先阅读:
  - `Dev_docs/PROJECT_BRIEF.md`
  - `Dev_docs/TREE_AND_ANCHOR.md`
  - `docs/student_parallel_tasks_v1.md`

## Student Integration Agent

- 负责:
  - `src/agents/student/agent.py`
  - `src/agents/__init__.py`
  - 必要时补充 `tests/student/integration/*`
- 不负责:
  - 重定义 memory、retrieval、skills 的内部 contract
  - 改写 teacher workflow
- 优先阅读:
  - `Dev_docs/FLOW.md`
  - `Dev_docs/CONTRACT.md`
  - `Dev_docs/TREE_AND_ANCHOR.md`

## Teacher Workflow Agent

- 负责:
  - `src/main.py`
  - `src/workflows/teacher_workflow.py`
  - `src/pipelines/file_parser_pipeline.py`
  - `src/pipelines/generate_pipeline.py`
  - 对应集成测试
- 不负责:
  - 学生侧 session/memory/retrieval 内部实现
- 优先阅读:
  - `Dev_docs/PROJECT_BRIEF.md`
  - `Dev_docs/FLOW.md`
  - 现有 `tests/generate/*` 与 `tests/parser/*`
