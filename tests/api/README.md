# API 测试套件

完整覆盖 32 个 HTTP 端点的 pytest 集成测试，全部使用 FastAPI ``TestClient``，不依赖运行中的 uvicorn，不污染你的真实 MySQL。

## 文件分布

| 文件 | 覆盖范围 | 测试数 |
|---|---|---|
| `conftest.py` | 共享 fixture（DB 隔离、agent/ASR mock、seed 工厂） | — |
| `test_health.py` | `/health`、`/`、`/panel/` | 3 |
| `test_lesson_endpoints.py` | `/api/v1/lesson/*`（18 端点） | 32 |
| `test_qa_endpoints.py` | `/api/v1/qa/*`（4 端点） | 10 |
| `test_progress_endpoints.py` | `/api/v1/progress/*`（2 端点） | 6 |
| `test_platform_endpoints.py` | `/api/v1/platform/*`（2 端点） | 7 |
| `test_kb_endpoints.py` | `/internal/kb/*`（5 端点） | 11 |
| `test_response_contract.py` | 跨切面：响应 envelope / CORS / 签名跳过 / 404 | 9 |
| `test_config.py` | `Settings` 解析单元测试 | 4 |
| **合计** | **32 端点** | **82** |

## 一键运行

```bash
# 仅 API 测试（< 5 秒）
.venv/bin/python -m pytest tests/api/ -q -W ignore

# 全部测试（API + 既有 233 个 student/parser/generate）
.venv/bin/python -m pytest tests/ --ignore=tests/student/integration -q -W ignore

# 看覆盖率
.venv/bin/python -m pytest tests/api/ --cov=src/api --cov-report=term -q -W ignore

# 只跑某个 router
.venv/bin/python -m pytest tests/api/test_lesson_endpoints.py -v
```

## 关键设计决策

1. **隔离的 SQLite**：`conftest._reset_test_db` 在 session 启动时删除 `_tmp_test.db`，每次 `pytest` 运行都是 fresh state。**不会触碰** `.env` 里配的真实 MySQL。

2. **强制重建 engine**：因为既有 student / parser 测试可能更早 import 了 `src.api.app` 并构建过指向 MySQL 的 engine，API conftest 的 `app` fixture 会显式调用 `_build_engine_with_url(SQLite URL)` 覆盖掉。

3. **背景任务短路**：lesson router 用 `BackgroundTasks.add_task` 触发 parse / script / audio / render，这些会调真 LLM、TTS、PPT 渲染。`_disable_background_tasks` autouse fixture 把它替换成 no-op，让所有 API 测试只验证**同步 request → response 契约**。

4. **mock 外部服务**：`mock_voice_to_text`、`mock_run_qa_interact` 这两个 fixture 把 ASR 网络调用和学生 Agent 调用都替换成确定性 stub，避免测试时打开网络。

5. **Seed factories**：`seeded_parse_task / seeded_script / seeded_audio_task / seeded_kb` 4 个 fixture 提供"完整"的数据库行，让每个 200 路径测试只需 1-3 行。

## 添加新测试时

```python
def test_new_endpoint(client, seeded_parse_task):
    r = client.post("/api/v1/lesson/xxx", json={"lessonId": seeded_parse_task.parse_id})
    assert r.status_code == 200
    assert r.json()["code"] == 200
```

如果你的新端点：

- **调用 LLM** → 用 `mock_run_qa_interact` 或自己写一个 `monkeypatch.setattr(...)`
- **调用 ASR** → 用 `mock_voice_to_text`
- **写文件** → 用 `tmp_path` fixture（pytest 内置）
- **触发 background task** → 已经被短路成 no-op，无需关心
- **依赖另一个端点先建数据** → 加一个 `seeded_*` fixture 到 `conftest.py`，不要在测试里手写 `client.post(...)` 链

## 不在覆盖范围

- ✗ **真正的 LLM 集成**：`tests/student/integration/test_student_agent.py` 才是这一块的归口（它依赖 `claude_agent_sdk`，需要单独装）
- ✗ **PPT 渲染、edge-tts、ASR 网络**：这些是 e2e 测试的范围，应单独跑
- ✗ **签名校验中间件主路径**：`DEBUG=true` 跳过；生产环境的签名验证由 `tests/test_middleware*.py` 单元测试覆盖（如有）

## CI 推荐姿势

```yaml
# .github/workflows/test.yml 类似
- run: .venv/bin/python -m pytest tests/api/ tests/student/test_*.py tests/parser/ -q
```

API 测试 < 5 秒，加上既有快速测试整体 < 60 秒。
