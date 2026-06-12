# E2E 集成测试套件

**真实** 端到端集成测试 — 调真 LLM、真 edge-tts、真 PPT 渲染、真 SQLAlchemy commit。

> ⚠️ **默认 skip**：这些测试依赖外部服务（LLM API、edge-tts CDN）和你的 ``.env`` 配置。普通 `pytest` 运行不会跑它们，避免 CI 误触和本地误网络调用。

## 一键运行

```bash
# 默认（skip）
.venv/bin/python -m pytest tests/e2e/                  # → 13 skipped, 0.03s

# 启用 e2e（任选其一）
RUN_E2E=1 .venv/bin/python -m pytest tests/e2e/        # → 13 passed, ~50s
.venv/bin/python -m pytest tests/e2e/ --run-e2e        # 同上

# 单独跑某个阶段
RUN_E2E=1 .venv/bin/python -m pytest tests/e2e/test_e2e_parse.py -v -s
```

## 测试范围

| 文件 | Phase | 真实调用 | 测试数 | 典型耗时 |
|---|---|---|---|---|
| `test_e2e_parse.py` | PDF 解析 | LLM × 1（structuring） | 3 | ~5 s |
| `test_e2e_script.py` | 讲稿生成 | LLM × N（每 section 1 次） | 3 | ~13 s |
| `test_e2e_audio.py` | 音频合成 | edge-tts CDN | 4 | ~10 s |
| `test_e2e_full_workflow.py` | 一键流水线 + PPT 渲染 | LLM + python-pptx | 3 | ~25 s |
| **合计** | — | — | **13** | **~50 s** |

## 测试 PDF

`conftest.py::tiny_pdf` 在每个 session 开始时**动态生成**一份 1 页中文 PDF（牛顿第一定律），用 PyMuPDF 写入 ``tmp_path``。这样：

- token 消耗最小（< 500 token / 次 LLM 调用）
- 不依赖仓库里任何特定 PDF
- 删除后自动重建

如需测多页 PDF（比如压力测试），用 `real_pdf` fixture 切到仓库根目录的赛题 PDF（16 页）。

## 数据库隔离

`conftest.py` 使用专用的 `_e2e_test.db` SQLite 文件，**不动你的 MySQL**。该文件在 session 启动时被删除，session 结束后保留（方便排查问题）。

## 设计取舍

1. **每阶段独立可跑**：每个 e2e 测试都从头开始 parse → script → audio，不依赖前一个测试的产物。代价是 LLM 多调几次，收益是任何一个失败都好定位。

2. **优雅降级 (`pytest.skip`)**：edge-tts 不通、PPT 渲染失败、`.env` 缺 LLM keys 时，相关测试会 `skip` 而不是 `fail`，让你看清问题在外部环境而不是项目代码。

3. **同步驱动而非 BackgroundTasks**：FastAPI 的 BackgroundTasks 在 router 里用，但 e2e 测试通过 `_disable_background_tasks` autouse fixture 把它替换成 no-op，然后**直接调** `lesson_service.run_*` 让结果同步可断言。

4. **对终态的契约式断言**：例如 audio task 我们断言 "completed → file exists / failed → error_message 非空"，而非具体的字段值，让测试对内部实现细节不敏感。

## 何时该新增 e2e 测试

- 引入了新的**外部服务依赖**（新 LLM provider、新 TTS、新存储）
- 修改了**多模块串联**的契约（比如 parse 输出格式 → script 输入格式）
- 排查的 bug 是 "单元测试都过但联调挂了"

不该新增 e2e 测试的场景：
- 单个函数的逻辑验证 → 单元测试
- HTTP 状态码 / response shape → `tests/api/`
- mock 即可覆盖的逻辑分支 → 单元测试

## 故障排查

| 失败信息 | 含义 | 处理 |
|---|---|---|
| `parse failed: 'LLM ...'` | `.env` 里 LLM_* 配置错或网络不通 | 单跑 `python -c "from src.agents.file_parser import ..."` 验证 |
| `edge-tts unreachable: ...` | 微软 CDN 被墙 / 防火墙挡 | 加代理或 skip 即可，不是项目 bug |
| `rendered_ppt_path` 没生成 | python-pptx / 字体缺失 | 看 `lesson.error_message` 字段 |
| 数据库锁定 | 并发跑了多个 e2e session | 删 `tests/e2e/_e2e_test.db` |

## CI 集成

推荐在 CI 中**只跑标准测试，跳过 e2e**：

```yaml
- run: .venv/bin/python -m pytest tests/ --ignore=tests/student/integration -q
  # 上面命令会自动 skip e2e（默认行为）

# 单独的 e2e job（如果 CI 网络条件许可）
- name: E2E (optional)
  if: github.event_name == 'workflow_dispatch'
  env:
    RUN_E2E: 1
  run: .venv/bin/python -m pytest tests/e2e/ -v
```
