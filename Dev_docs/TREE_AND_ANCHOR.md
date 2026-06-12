# Tree And Anchor

## Directory Tree

```text
E:\ChaoXingAgent
├─ Dev_docs
├─ docs
├─ src
│  ├─ agents
│  │  ├─ file_parser.py
│  │  ├─ generate.py
│  │  └─ student
│  │     └─ agent.py
│  ├─ extractors
│  ├─ memory
│  ├─ pipelines
│  ├─ schemas
│  ├─ skills
│  ├─ utils
│  │  ├─ extractors
│  │  ├─ renderers
│  │  └─ student
│  └─ workflows
└─ tests
   ├─ generate
   ├─ parser
   └─ student
```

## Global Worker Constraints

- 允许在已授权目录内添加辅助函数完成实现。
- 不得修改这里冻结的关键公开签名，除非先更新 `Dev_docs` 并明确说明原因。
- 不得把既定能力迁移到平行新文件形成影子实现。
- 不得跨模块重写他人负责的边界。
- 学生侧新增能力必须继续消费既有 teacher artifacts，而不是重定义 teacher 输出。
- 底层模块可以增强实现，但外部 response contract 必须保持稳定。

## File Anchor List

`E:\ChaoXingAgent\src\main.py # CLI entrypoint for top-level workflow execution, not business orchestration logic`

- `def main(argv: Optional[Sequence[str]] = None) -> int`

`E:\ChaoXingAgent\src\workflows\teacher_workflow.py # Compose parser, generator, optional rendering, and artifact output for the teacher path`

- `def run_teacher_workflow(teacher_input: dict, *, ...) -> dict`
- `def build_teacher_workflow_stages(teacher_input: dict, *, ...) -> dict`

Special Constraints:
- Keep teacher workflow as orchestration only.
- Do not move parser or generate business logic into this file.

`E:\ChaoXingAgent\src\pipelines\file_parser_pipeline.py # Convert uploaded assets into parsed units and stable structured lesson content`

- `def run_file_parser_pipeline(request: ParserInput, logger=None) -> dict`

Special Constraints:
- Output must remain consumable by teacher generation and student retrieval.

`E:\ChaoXingAgent\src\pipelines\generate_pipeline.py # Transform structured lesson content into outline, script, and slide artifacts`

- `def run_generate_pipeline(generate_input: GenerateInput, llm_callable: Optional[Callable[..., Any]] = None, ..., section_cache: Optional[Dict[str, PresentationSection]] = None) -> dict`

Special Constraints:
- Preserve fallback generation path when LLM output is missing or invalid.

`E:\ChaoXingAgent\src\schemas\student_schemas.py # Freeze the external student request/response contract and retrieval context types`

- `class KnowledgePointMatch(SchemaModel)`
- `class RetrievedContextItem(SchemaModel)`
- `class StudentAgentRequest(BaseRequest)`
- `class StudentAgentResponse(BaseResponse)`

Special Constraints:
- Treat field names and validation rules here as external contract.

`E:\ChaoXingAgent\src\agents\student\agent.py # Student-turn orchestrator that coordinates QA, decision, session/progress updates, and response assembly`

- `def run_student_agent(request: StudentAgentRequest | dict) -> dict`
- `def build_student_agent_turn(request: StudentAgentRequest | dict) -> dict`

Special Constraints:
- Keep this file orchestration-focused.
- Do not embed storage or retrieval implementations directly here.

`E:\ChaoXingAgent\src\memory\session_store.py # Persist and mutate student session snapshots`

- `class SessionStore`

`E:\ChaoXingAgent\src\memory\history.py # Persist and query QA history records for a session`

- `class QAHistoryStore`

`E:\ChaoXingAgent\src\memory\condenser.py # Compress long-running student conversation history into a smaller context`

- `class StudentCondenser`

`E:\ChaoXingAgent\src\utils\student\embedder.py # Wrap embedding creation for student retrieval`

- `class Embedder`

`E:\ChaoXingAgent\src\utils\student\vector_store.py # Store and query vectorized lesson chunks for student retrieval`

- `class VectorStore`

`E:\ChaoXingAgent\src\utils\student\hybrid_retriever.py # Combine lexical and vector retrieval into context items`

- `class HybridRetriever`

`E:\ChaoXingAgent\src\utils\student\content_getter.py # Perform exact access to structured lesson content and script blocks`

- `class ContentGetter`

Special Constraints:
- `ContentGetter` is for exact fetches, not semantic search.

`E:\ChaoXingAgent\src\skills\__init__.py # Load student teaching skills from the on-disk skill set`

- `def load_skills(...)`

Special Constraints:
- Keep one skill per directory with one `SKILL.md`.
