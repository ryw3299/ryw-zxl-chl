# AI 互动智课服务系统 — 接口设计文档

> 版本：v1.2.0 | 更新日期：2026-04-03  
> 在线文档：启动服务后访问 `http://<host>:8000/docs`（Swagger UI）或 `/redoc`（ReDoc）  
> v1.2.0 变更：学生侧 Agent 重构（后端编排 + 知识库预索引 + 真实 LLM 接入），新增内部知识库管理接口

---

## 一、设计总则

### 1.1 设计目标

遵循超星开放 API 设计规范中"开放式框架、标准化接口、可扩展适配"核心要求，构建支持"课件解析 → 智课生成 → 实时问答 → 进度适配"全流程的开放 API 体系，确保后续可无缝对接泛雅平台及各类主流教育平台。

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **开放性** | 松耦合模块化设计，接口参数与返回格式标准化，支持跨平台、跨终端集成 |
| **专业性** | 贴合教育场景特性，接口功能覆盖教学全流程 |
| **安全性** | 所有接口均需 MD5 签名验证，敏感数据加密传输 |
| **可扩展性** | 预留功能扩展字段与版本控制机制 |
| **易用性** | 接口命名简洁明了，参数设计精简，返回结果结构化 |

### 1.3 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Web 框架 | FastAPI 0.100+ | 异步高性能，自动生成 OpenAPI 文档 |
| 数据库 | MySQL 8.0+（InnoDB） | utf8mb4 编码，支持事务 |
| ORM | SQLAlchemy 2.0（Mapped） | 声明式模型，类型安全 |
| 配置管理 | pydantic-settings | 环境变量 + `.env` 文件 |
| AI 推理 | OpenAI 兼容 LLM API | 课件解析、脚本生成、问答交互 |
| 后台任务 | FastAPI BackgroundTasks | 异步解析、异步生成 |

---

## 二、通用规范

### 2.1 接口协议与版本

- **协议**：HTTP/HTTPS（推荐 HTTPS 加密传输）
- **Base URL**：`/api/v1`
- **请求方法**：POST（提交/生成/查询类）、GET（系统检查类）
- **数据格式**：请求与返回数据统一采用 JSON 格式，编码 UTF-8
- **版本控制**：URL 中包含版本号 `/v1`，主版本号变更表示不兼容调整

### 2.2 签名验证机制

所有 `/api/` 开头的接口均需携带签名参数（`DEBUG=true` 时跳过验证）。

**签名算法**：

```
enc = MD5( 参数有序拼接 + staticKey + time )
```

**计算步骤**：

1. 收集所有非空请求参数（排除 `enc` 和 `time`）
2. 按参数名 ASCII 升序排列
3. 拼接为 `key1value1key2value2...` 格式
4. 追加 `staticKey`（双方协商的固定密钥）和 `time`（当前时间字符串）
5. 对拼接结果计算 MD5，取大写十六进制

**请求中的签名参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enc` | String | 是 | MD5 签名值（32 位大写十六进制） |
| `time` | String | 是 | 当前时间，格式 `yyyy-MM-ddHH:mm:ss` 或 `yyyy-MM-dd HH:mm:ss` |

**验证规则**：

- 签名有效窗口：默认 300 秒（可配置 `SIGNATURE_TIMEOUT_SECONDS`）
- 验证失败返回 HTTP 403：`{"code": 403, "msg": "签名验证失败"}`
- 跳过验证的路径：`/`、`/docs`、`/redoc`、`/openapi.json`、`/health`

**实现位置**：`src/api/middleware.py` → `SignatureVerifyMiddleware`

### 2.3 统一响应格式

所有接口均返回以下 JSON 结构：

```json
{
    "code": 200,
    "msg": "操作成功",
    "data": { },
    "requestId": "req20240520001"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | Integer | HTTP 状态码：200 成功，4xx 客户端错误，5xx 服务端错误 |
| `msg` | String | 状态描述文本 |
| `data` | Object / null | 业务数据（成功时返回，格式随接口变化；失败时为 null） |
| `requestId` | String | 请求唯一标识（UUID 前 16 位，前缀 `req`），用于问题排查 |

### 2.4 错误码说明

| 错误码 | HTTP 状态 | 说明 | 处理建议 |
|--------|----------|------|---------|
| 200 | 200 OK | 操作成功 | 正常处理返回数据 |
| 400 | 400 Bad Request | 参数错误 | 检查参数格式、必填项是否完整 |
| 403 | 403 Forbidden | 签名验证失败 | 检查签名参数、密钥、时间戳 |
| 404 | 404 Not Found | 资源不存在 | 确认课件 ID、脚本 ID 等资源标识是否有效 |
| 422 | 422 Unprocessable | 请求体校验失败 | 检查 JSON 字段类型是否正确（FastAPI 自动校验） |
| 500 | 500 Internal Error | 服务端错误 | 联系技术支持，提供 requestId 排查 |

**实现位置**：`src/api/app.py` → 全局异常处理器 `http_exception_handler` / `general_exception_handler`

---

## 三、接口总览

共 **23 个接口**，分布在 4 个核心模块 + 1 个内部管理模块 + 1 个系统模块：

| # | 模块 | 接口 | 方法 | 路径 | 功能 |
|---|------|------|------|------|------|
| 1 | 智课生成 | **一键智课生成** | POST | `/api/v1/lesson/generate` | 流水线：解析→脚本→PPT |
| 2 | 智课生成 | **查询流水线状态** | POST | `/api/v1/lesson/generateStatus` | 查询流水线各步骤进度 |
| 3 | 智课生成 | 课件上传与解析 | POST | `/api/v1/lesson/parse` | 提交 PPT/PDF 课件解析任务 |
| 4 | 智课生成 | 查询解析状态 | POST | `/api/v1/lesson/parseStatus` | 查询课件解析进度与结果 |
| 5 | 智课生成 | 智课脚本生成 | POST | `/api/v1/lesson/generateScript` | 生成结构化讲授脚本 |
| 6 | 智课生成 | 查询脚本状态 | POST | `/api/v1/lesson/scriptStatus` | 查询脚本生成进度与结果 |
| 7 | 智课生成 | **PPT 课件渲染** | POST | `/api/v1/lesson/renderPPT` | 基于脚本渲染教学 PPTX |
| 8 | 智课生成 | **PPT 文件下载** | GET | `/api/v1/lesson/download/{id}` | 下载渲染后的 PPTX |
| 9 | 智课生成 | 语音合成 | POST | `/api/v1/lesson/generateAudio` | 将脚本转换为语音音频 |
| 10 | 智课生成 | 查询音频状态 | POST | `/api/v1/lesson/audioStatus` | 查询语音合成进度与结果 |
| 11 | 智课生成 | 教师脚本编辑 | POST | `/api/v1/lesson/editScript` | 教师手动编辑讲授脚本 |
| 12 | 实时问答 | 问答交互 | POST | `/api/v1/qa/interact` | 学生提问 → AI 解答 |
| 13 | 实时问答 | 语音提问识别 | POST | `/api/v1/qa/voiceToText` | 语音转文字 |
| 14 | 学习进度 | 学习进度追踪 | POST | `/api/v1/progress/track` | 记录学习进度 |
| 15 | 学习进度 | 学习节奏调整 | POST | `/api/v1/progress/adjust` | 调整讲授节奏 |
| 16 | 平台对接 | 课程信息同步 | POST | `/api/v1/platform/syncCourse` | 同步外部平台课程 |
| 17 | 平台对接 | 用户信息同步 | POST | `/api/v1/platform/syncUser` | 同步外部平台用户 |
| 18 | 系统 | 健康检查 | GET | `/health` | 检查服务运行状态 |
| 19 | 知识库(内部) | 列出知识库 | GET | `/internal/kb/list` | 查询所有知识库 |
| 20 | 知识库(内部) | 知识库详情 | GET | `/internal/kb/status/{kb_id}` | 查询知识库状态与来源 |
| 21 | 知识库(内部) | 创建知识库 | POST | `/internal/kb/create` | 创建空知识库 |
| 22 | 知识库(内部) | 添加来源 | POST | `/internal/kb/addSources` | 向知识库添加 lesson 来源 |
| 23 | 知识库(内部) | 构建索引 | POST | `/internal/kb/build` | 触发知识库索引构建 |

> 接口 1-2 为**流水线（Pipeline）接口** — 教师端主入口，一次提交自动跑完全流程。  
> 接口 3-11 为**细粒度接口** — 供需要精细控制各步骤的场景使用。  
> 接口 19-23 为**内部管理接口** — 用于知识库管理，不属于对外开放 API，挂载在 `/internal` 前缀下。

---

## 四、流水线接口（Pipeline）

> **路由文件**：`src/api/routers/lesson.py`  
> **服务层**：`src/api/services/lesson_service.py` → `run_full_workflow()`  
> **编排层**：`src/workflows/teacher_workflow.py` → `build_teacher_workflow_stages()`

### 4.0 设计说明

系统提供**两层接口**：

- **流水线接口**（`/lesson/generate`）— 教师端主入口，一次提交课件，后台自动编排完整 pipeline（课件解析 → 脚本生成 → PPT 渲染），直接复用已有的 `teacher_workflow` 编排层。前端只需轮询一个总状态。
- **细粒度接口**（`/lesson/parse`、`/lesson/generateScript` 等）— 供需要精细控制各步骤的场景使用，每个环节可独立调用和重试。

两层共享同一套数据库记录（`parse_tasks`、`scripts`、`lessons`），流水线执行完成后的结果也可通过细粒度状态接口查询。

### 4.1a 一键智课生成（流水线）

上传课件后自动执行完整流水线，一次提交，通过 `generateStatus` 查询整体进度。

- **接口地址**：`POST /api/v1/lesson/generate`
- **执行模式**：异步（`BackgroundTasks`）— 复用 `build_teacher_workflow_stages`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `schoolId` | String | 是 | 学校 ID | `"sch10001"` |
| `userId` | String | 是 | 用户 ID（教师工号） | `"tea20001"` |
| `courseId` | String | 是 | 课程 ID | `"cou30001"` |
| `fileType` | String | 是 | 课件文件类型 | `"ppt"` / `"pdf"` |
| `fileUrl` | String | 是 | 课件 URL 或本地路径 | `"http://xxx.com/123.pdf"` |
| `teachingStyle` | String | 否 | 讲授风格（默认 `"standard"`） | `"standard"` / `"detailed"` / `"concise"` |
| `customOpening` | String | 否 | 自定义开场白 | `"同学们好..."` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据

```json
{
    "code": 200,
    "msg": "智课生成流水线已启动",
    "data": {
        "lessonId": "lesson20240520001",
        "lessonName": "",
        "workflowStatus": "processing",
        "steps": [
            {"step": "课件解析", "status": "processing"},
            {"step": "脚本生成", "status": "pending"},
            {"step": "PPT 渲染", "status": "pending"}
        ]
    },
    "requestId": "req20240520001"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 生成 lessonId (UUID 前缀 "lesson")
  ├─ 2. 创建 Lesson 记录 (status = "generating")
  ├─ 3. 注册后台任务 _run_workflow_in_background
  └─ 4. 立即返回 {lessonId, workflowStatus: "processing"}

后台任务执行（复用 teacher_workflow 编排层）：
  │
  ├─ 5. 若 fileUrl 为 HTTP → 下载到 data/uploads/
  │
  ├─ 6. build_teacher_workflow_stages(teacher_input)
  │      ├── file_parser Agent: 课件解析 → 结构化内容
  │      ├── generate Agent:    脚本生成 → 讲授脚本 + PPT 大纲
  │      └── render_ppt_outline: PPT 渲染 → PPTX 文件
  │
  ├─ 7. 创建 parse_tasks 记录 (status = "completed")
  ├─ 8. 创建 scripts 记录 (status = "completed")
  ├─ 9. 更新 lessons 记录:
  │      lesson_name, parse_id, script_id,
  │      structured_content, ppt_outline,
  │      rendered_ppt_path, status = "draft"
  │
  └─ 10. 若任何步骤失败 → lesson.status = "failed"
         → parse_tasks.error_message = 错误信息
```

**关联数据库表**：`lessons`、`parse_tasks`、`scripts`

### 4.1b 查询流水线状态

查询智课生成流水线的整体进度，包含各步骤执行状态。

- **接口地址**：`POST /api/v1/lesson/generateStatus`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `lessonId` | String | 是 | 智课 ID |
| `enc` | String | 是 | 签名信息 |
| `time` | String | 是 | 当前时间 |

#### 返回数据（完成状态）

```json
{
    "code": 200,
    "msg": "查询成功",
    "data": {
        "lessonId": "lesson20240520001",
        "lessonName": "材料力学-梁弯曲理论",
        "workflowStatus": "completed",
        "steps": [
            {"step": "课件解析", "status": "completed"},
            {"step": "脚本生成", "status": "completed"},
            {"step": "PPT 渲染", "status": "completed"}
        ],
        "parseId": "lesson20240520001",
        "scriptId": "script20240520001",
        "renderedPptUrl": "/api/v1/lesson/download/lesson20240520001",
        "errorMessage": null
    },
    "requestId": "req20240520002"
}
```

#### 实现逻辑

```
1. 查询 lessons 表 WHERE lesson_id = ?
2. 若不存在 → HTTP 404
3. 派生各步骤状态:
   - 课件解析: 查 parse_tasks 表 → task_status
   - 脚本生成: 查 scripts 表 → task_status
   - PPT 渲染: 检查 lesson.rendered_ppt_path 是否非空
4. 派生总状态:
   - lesson.status == "generating" → "processing"
   - lesson.status == "failed"     → "failed"
   - 其他                          → "completed"
5. 返回 {lessonId, workflowStatus, steps[], parseId,
         scriptId, renderedPptUrl, errorMessage}
```

### 4.1c PPT 课件渲染

基于已生成的脚本与 PPT 大纲，渲染生成教学 PPTX 文件。可在脚本编辑后重新渲染。

- **接口地址**：`POST /api/v1/lesson/renderPPT`
- **执行模式**：异步（`BackgroundTasks`）
- **前置条件**：智课已完成脚本生成，`ppt_outline` 已存储

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `lessonId` | String | 是 | 智课 ID |
| `enc` | String | 是 | 签名信息 |
| `time` | String | 是 | 当前时间 |

#### 返回数据

```json
{
    "code": 200,
    "msg": "PPT 渲染任务已提交",
    "data": {
        "lessonId": "lesson20240520001",
        "taskStatus": "processing"
    },
    "requestId": "req20240520003"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 查询 lessons 表，检查 ppt_outline 是否存在
  │      不存在 → HTTP 400 "请先完成脚本生成"
  │
  ├─ 2. 注册后台任务 _run_render_in_background(lessonId)
  │
  └─ 3. 立即返回 {lessonId, taskStatus: "processing"}

后台任务执行 (render_ppt_for_lesson):
  │
  ├─ 4. 从 lessons.ppt_outline 重建 PPTOutline 模型
  ├─ 5. 从 scripts.generate_output 重建 LessonScript 模型
  ├─ 6. 从 parse_tasks.parser_output 重建 source_assets + source_pages
  ├─ 7. 调用 render_ppt_outline() → 输出到 data/renders/{lessonId}.pptx
  └─ 8. 更新 lessons.rendered_ppt_path
```

**渲染器**：`src/utils/renderers/pptx_renderer.py`（1700+ 行，支持页面截图嵌入、讲稿覆盖、知识点卡片）

### 4.1d PPT 文件下载

下载已渲染完成的教学 PPTX 文件。

- **接口地址**：`GET /api/v1/lesson/download/{lessonId}`
- **返回类型**：`application/vnd.openxmlformats-officedocument.presentationml.presentation`

#### 实现逻辑

```
1. 查询 lessons 表 WHERE lesson_id = ?
2. 若不存在或 rendered_ppt_path 为空 → HTTP 404
3. 检查文件是否存在于磁盘 → 不存在则 HTTP 404
4. 返回 FileResponse (Content-Disposition: attachment)
```

---

## 五、模块一：智课细粒度接口（`/api/v1/lesson/*`）

> **路由文件**：`src/api/routers/lesson.py`  
> **服务层**：`src/api/services/lesson_service.py`  
> **AI Agent**：`src/agents/file_parser.py`（解析）、`src/agents/generate.py`（生成）

### 5.1 课件上传与解析

接收 PPT/PDF 格式课件，异步解析知识点层级、公式图表、重点标注等结构化信息。

- **接口地址**：`POST /api/v1/lesson/parse`
- **执行模式**：异步（`BackgroundTasks`）—— 立即返回任务 ID，后台执行解析

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `schoolId` | String | 是 | 学校 ID | `"sch10001"` |
| `userId` | String | 是 | 用户 ID（教师工号） | `"tea20001"` |
| `courseId` | String | 是 | 课程 ID | `"cou30001"` |
| `fileType` | String | 是 | 课件文件类型 | `"ppt"` / `"pdf"` |
| `fileUrl` | String | 是 | 课件 URL 或本地路径 | `"http://xxx.com/123.pdf"` |
| `isExtractKeyPoint` | Boolean | 否 | 是否自动提取重点（默认 true） | `true` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据

```json
{
    "code": 200,
    "msg": "课件解析任务已提交",
    "data": {
        "parseId": "parse178fcfa33d734bee",
        "fileInfo": {
            "fileName": "材料力学-梁弯曲理论.pptx",
            "fileSize": 2048000,
            "pageCount": 0
        },
        "structurePreview": {
            "chapters": []
        },
        "taskStatus": "processing"
    },
    "requestId": "req3c318cdb1d524b31"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. lesson_service.create_parse_task()
  │      → 生成 parseId (UUID 前缀 "parse")
  │      → 从 fileUrl 提取 fileName
  │      → 写入 parse_tasks 表 (status = "processing")
  │
  ├─ 2. 注册后台任务 _run_parse_in_background(parseId)
  │
  └─ 3. 立即返回 {parseId, taskStatus: "processing"}

后台任务执行：
  │
  ├─ 4. 若 fileUrl 是 HTTP 链接 → urlretrieve 下载到 data/uploads/
  │
  ├─ 5. 调用 file_parser Agent:
  │      build_file_parser_stages(parser_request, env_path)
  │      → 文件加载 → LLM 解析 → 结构化输出
  │      → 得到 ParserOutput (pages, sections, knowledge_points)
  │
  ├─ 6. _build_structure_preview(sections, pages)
  │      → 构建 chapters → subChapters 层级结构
  │      → 标记 isKeyPoint (有知识点的页面)
  │
  ├─ 7. _ensure_lesson() → 创建/更新 lessons 表记录
  │
  └─ 8. 更新 parse_tasks 表:
         task_status = "completed"
         page_count = len(pages)
         structure_preview = JSON(chapters)
         parser_output = JSON(完整解析输出)
```

**关联数据库表**：`parse_tasks`、`lessons`

---

### 5.2 查询解析任务状态

根据解析任务 ID 查询课件解析进度与结果。

- **接口地址**：`POST /api/v1/lesson/parseStatus`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `parseId` | String | 是 | 解析任务 ID | `"parse20240520001"` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据（完成状态）

```json
{
    "code": 200,
    "msg": "查询成功",
    "data": {
        "parseId": "parse20240520001",
        "fileInfo": {
            "fileName": "材料力学-梁弯曲理论.pptx",
            "fileSize": 2048000,
            "pageCount": 25
        },
        "structurePreview": {
            "chapters": [
                {
                    "chapterId": "chap001",
                    "chapterName": "梁弯曲理论基础",
                    "subChapters": [
                        {
                            "subChapterId": "sub001",
                            "subChapterName": "平面假设的定义",
                            "isKeyPoint": true,
                            "pageRange": "3-5"
                        }
                    ]
                }
            ]
        },
        "taskStatus": "completed",
        "errorMessage": null
    },
    "requestId": "req20240520001"
}
```

#### 实现逻辑

```
1. lesson_service.get_parse_task(db, parseId)
   → 查询 parse_tasks 表 WHERE parse_id = ?
2. 若记录不存在 → 返回 HTTP 404
3. 反序列化 task.structure_preview (JSON → dict)
4. 组装响应：fileInfo + structurePreview + taskStatus + errorMessage
```

---

### 5.3 智课脚本生成

基于课件解析结果，调用 LLM 生成含开场白、讲解、过渡语的结构化讲授脚本。

- **接口地址**：`POST /api/v1/lesson/generateScript`
- **执行模式**：异步（`BackgroundTasks`）
- **前置条件**：关联的解析任务必须已完成（`taskStatus = "completed"`）

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `parseId` | String | 是 | 课件解析任务 ID | `"parse20240520001"` |
| `teachingStyle` | String | 否 | 讲授风格（默认 `"standard"`） | `"standard"` / `"detailed"` / `"concise"` |
| `speechSpeed` | String | 否 | 语速适配（默认 `"normal"`） | `"slow"` / `"normal"` / `"fast"` |
| `customOpening` | String | 否 | 自定义开场白 | `"同学们好，今天我们学习..."` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据（查询完成状态后）

```json
{
    "code": 200,
    "msg": "查询成功",
    "data": {
        "scriptId": "script20240520001",
        "scriptStructure": [
            {
                "sectionId": "sec001",
                "sectionName": "开场白",
                "content": "同学们好，今天我们将深入学习材料力学中的梁弯曲理论...",
                "duration": 15,
                "relatedChapterId": "sec001",
                "keyPoints": ["梁弯曲理论概述"]
            },
            {
                "sectionId": "sec002",
                "sectionName": "平面假设的定义",
                "content": "平面假设是梁弯曲理论的基本假设...",
                "duration": 45,
                "relatedChapterId": "sec002",
                "keyPoints": ["平面假设核心内涵", "变形前后截面特性"]
            }
        ],
        "editUrl": "/script/edit?scriptId=script20240520001",
        "audioGenerateUrl": "/api/v1/lesson/generateAudio",
        "taskStatus": "completed"
    },
    "requestId": "req20240520002"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 校验 parseId 关联的解析任务是否存在且已完成
  │      不存在 → HTTP 404 / 未完成 → HTTP 400
  │
  ├─ 2. lesson_service.create_script()
  │      → 生成 scriptId (UUID 前缀 "script")
  │      → 写入 scripts 表 (status = "processing")
  │
  ├─ 3. 注册后台任务 _run_generate_in_background(scriptId)
  │
  └─ 4. 立即返回 {scriptId, taskStatus: "processing"}

后台任务执行：
  │
  ├─ 5. 从 parse_tasks 表读取 parser_output (完整解析结果)
  │
  ├─ 6. 根据 teachingStyle 构造 generate_instruction:
  │      "detailed" → "请生成详细的讲解内容，对每个知识点进行深入阐述"
  │      "concise"  → "请生成简洁的讲解内容，突出核心要点"
  │      "standard" → 无额外指令
  │
  ├─ 7. 调用 generate Agent:
  │      build_generate_stages(generate_request, env_path)
  │      → LLM 生成 LessonScript (script_blocks)
  │      → 每个 block 含 section_id, title, script_text, key_points
  │
  ├─ 8. _build_script_structure(stages)
  │      → 遍历 script_blocks
  │      → 计算 duration = max(10, 字符数 / 5)
  │      → 组装 {sectionId, sectionName, content, duration, keyPoints}
  │
  ├─ 9. 更新 lessons 表：关联 script_id、存储 ppt_outline
  │
  └─ 10. 更新 scripts 表:
          task_status = "completed"
          script_structure = JSON(脚本结构)
          generate_output = JSON(完整生成输出)
```

**关联数据库表**：`scripts`、`parse_tasks`、`lessons`

---

### 5.4 查询脚本生成状态

- **接口地址**：`POST /api/v1/lesson/scriptStatus`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `scriptId` | String | 是 | 脚本 ID |
| `enc` | String | 是 | 签名信息 |
| `time` | String | 是 | 当前时间 |

#### 实现逻辑

```
1. lesson_service.get_script(db, scriptId)
   → 查询 scripts 表 WHERE script_id = ?
2. 若记录不存在 → HTTP 404
3. 反序列化 script.script_structure (JSON → list)
4. 组装响应：scriptId + parseId + lessonId + teachingStyle
              + scriptStructure + editUrl + audioGenerateUrl
              + taskStatus + errorMessage
```

---

### 5.5 语音合成

将结构化脚本转换为语音音频，支持对接通用 TTS 服务。

- **接口地址**：`POST /api/v1/lesson/generateAudio`
- **执行模式**：异步（`BackgroundTasks`）
- **前置条件**：关联的脚本必须已完成
- **当前状态**：预留接口框架，TTS 服务待接入

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `scriptId` | String | 是 | 脚本 ID | `"script20240520001"` |
| `voiceType` | String | 否 | 语音类型（默认 `"female_standard"`） | `"female_standard"` / `"male_professional"` |
| `audioFormat` | String | 否 | 音频格式（默认 `"mp3"`） | `"mp3"` / `"wav"` |
| `sectionIds` | Array\<String\> | 否 | 指定合成的章节 ID（默认全部） | `["sec001", "sec002"]` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据（查询完成状态后）

```json
{
    "code": 200,
    "msg": "查询成功",
    "data": {
        "audioId": "audio20240520001",
        "taskStatus": "completed",
        "audioUrl": "/data/audio/audio20240520001.mp3",
        "audioInfo": {
            "totalDuration": 600,
            "fileSize": 9600000,
            "format": "mp3",
            "bitRate": 128000
        },
        "sectionAudios": [
            {
                "sectionId": "sec001",
                "audioUrl": "/data/audio/section/sec001.mp3",
                "duration": 15
            }
        ]
    },
    "requestId": "req20240520003"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 校验 scriptId 关联的脚本是否存在且已完成
  │
  ├─ 2. lesson_service.create_audio_task()
  │      → 生成 audioId (UUID 前缀 "audio")
  │      → 写入 audio_tasks 表 (status = "processing")
  │
  └─ 3. 后台任务 run_audio_task():
         → 读取脚本的 script_structure
         → 计算 totalDuration = Σ(各章节 duration)
         → 估算 fileSize = totalDuration × 16000
         → 生成各章节 audioUrl
         → 更新 audio_tasks 表 (status = "completed")
         注: 当前为预估数据，接入 TTS 后替换为真实合成
```

**关联数据库表**：`audio_tasks`、`scripts`

---

### 5.6 查询音频状态

- **接口地址**：`POST /api/v1/lesson/audioStatus`
- **实现逻辑**：同 4.2/4.4 模式，查询 `audio_tasks` 表

---

### 5.7 教师脚本编辑

教师可对 AI 生成的讲授脚本进行手动编辑与调整，保存后覆盖原脚本结构。

- **接口地址**：`POST /api/v1/lesson/editScript`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `scriptId` | String | 是 | 脚本 ID |
| `scriptStructure` | Array\<Object\> | 是 | 编辑后的脚本结构（与生成返回格式一致） |
| `enc` | String | 是 | 签名信息 |
| `time` | String | 是 | 当前时间 |

#### 实现逻辑

```
1. lesson_service.edit_script(db, script_id, script_structure)
   → 查询 scripts 表 WHERE script_id = ?
   → 若不存在 → HTTP 404
   → 将 script_structure 序列化为 JSON 写入 scripts.script_structure
   → db.commit()
2. 返回更新后的完整脚本数据
```

**关联数据库表**：`scripts`

---

## 六、模块二：多模态实时问答（`/api/v1/qa/*`）

> **路由文件**：`src/api/routers/qa.py`  
> **服务层**：`src/api/services/qa_service.py`  
> **后端编排**：`src/services/student/context_builder.py`（Pre-RAG 上下文组装）  
> **AI Agent**：`src/agents/student/agent.py`（`StudentOpenHandsAgent`，基于 OpenHands SDK + 真实 LLM）

### 5.1 问答交互

接收学生文字/语音提问，调用 StudentOpenHandsAgent 进行工具驱动的 grounded QA，返回精准解答和教学决策，支持多轮交互。

- **接口地址**：`POST /api/v1/qa/interact`
- **执行模式**：同步（实时响应）

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `schoolId` | String | 是 | 学校 ID | `"sch10001"` |
| `userId` | String | 是 | 学生学号 | `"stu20001"` |
| `courseId` | String | 是 | 课程 ID | `"cou30001"` |
| `lessonId` | String | 是 | 智课 ID | `"lesson20240520001"` |
| `sessionId` | String | 是 | 会话 ID（多轮交互标识） | `"ses20240520001"` |
| `questionType` | String | 是 | 提问类型 | `"text"` / `"voice"` |
| `questionContent` | String | 是 | 提问内容 | `"平面假设为什么能简化梁弯曲问题？"` |
| `currentSectionId` | String | 否 | 当前学习章节 ID | `"sec002"` |
| `currentPage` | Integer | 否 | 当前学习页码（1-based） | `3` |
| `currentScriptBlockId` | String | 否 | 当前讲稿块 ID | `"script_2"` |
| `historyQa` | Array\<Object\> | 否 | 历史问答记录 | `[{"question":"...","answer":"..."}]` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据

```json
{
    "code": 200,
    "msg": "问答交互成功",
    "data": {
        "answerId": "ans20240520001",
        "answerContent": "平面假设之所以能简化梁弯曲问题，核心原因是它忽略了剪切变形对截面形状的影响...",
        "answerType": "text",
        "relatedKnowledge": {
            "knowledgeId": "平面假设",
            "knowledgeName": "平面假设",
            "relatedSectionId": "sec002"
        },
        "suggestions": [
            "平面假设的原因还能再展开吗？",
            "平面假设能举个例子吗？"
        ],
        "understandingLevel": "partial",
        "questionType": "reasoning",
        "nextAction": "supplement_then_resume",
        "reason": "先补充解释当前知识点，再回到原学习进度。",
        "matchedSectionId": "sec002",
        "matchedPage": 3,
        "targetSectionId": "sec002",
        "targetPage": 3
    },
    "requestId": "req20240520004"
}
```

#### 返回字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `answerId` | String | 回答 ID，可用于关联进度追踪 |
| `answerContent` | String | AI 生成的回答内容（中文，grounded 于课时内容） |
| `answerType` | String | `"text"` / `"mixed"` |
| `relatedKnowledge` | Object\|null | 关联知识点（从 Agent 的 matched_knowledge_points 或 references 提取） |
| `suggestions` | Array\<String\> | Agent 生成的追问建议（基于问题类型和匹配知识点动态生成） |
| `understandingLevel` | String | 学生理解程度：`"full"` / `"partial"` / `"none"` |
| `questionType` | String | Agent 识别的问题类型：`definition` / `reasoning` / `procedure` / `example` / `comparison` / `summary` / `chitchat` / `unknown` |
| `nextAction` | String\|null | 建议的下一步教学动作：`resume`（继续）/ `supplement_then_resume`（补充后继续）/ `reteach_slowly`（放慢重讲）/ `trigger_game`（互动巩固） |
| `reason` | String | 决策原因说明 |
| `matchedSectionId` | String\|null | 回答匹配到的章节 ID |
| `matchedPage` | Integer\|null | 回答匹配到的页码 |
| `targetSectionId` | String\|null | 建议跳转的章节 ID |
| `targetPage` | Integer\|null | 建议跳转的页码 |

#### 实现逻辑（v1.2 重构后）

```
请求到达
  │
  ├─ 1. qa_service.get_or_create_session()
  │      → 查询 qa_sessions 表 WHERE session_id = ?
  │      → 若不存在 → 创建新会话 (status = "active")
  │
  ├─ 2. context_builder.build_turn_context()  ← 后端编排(替代原来的 Agent Tool 调用)
  │      ├── _load_lesson_content()
  │      │   → 从 lessons 表加载 structured_content + lesson_script
  │      │   → 若课时数据不存在 → 返回 None → fallback 提示
  │      │
  │      ├── SessionService.get_or_init()
  │      │   → 从 MySQL qa_sessions 读 session 状态（替代临时 SQLite）
  │      │
  │      ├── ConversationService.load_recent_turns()
  │      │   → 从 data/conversations/{session_id}/turns.json 读最近 5 轮对话
  │      │   → 若无持久化记录 → fallback 到 API 传入的 historyQa
  │      │
  │      ├── classify_question_type()
  │      │   → 问题分类 (8 种：definition/reasoning/.../chitchat/unknown)
  │      │   → chitchat 类（如"你好"）跳过检索，直接回复
  │      │
  │      ├── RetrievalService.do_retrieval()
  │      │   → 优先查找 lesson 关联的知识库预建索引 (KB path)
  │      │   → 有 KB → 加载 FAISS + BM25 预建索引
  │      │   → 无 KB → fallback 到 RetrieverFactory 即时构建
  │      │   → 执行混合检索: 0.6×向量 + 0.4×BM25 + 位置偏置
  │      │   → 返回 top-5 chunks + exact_source
  │      │
  │      └── 打包成 StudentTurnContext 返回
  │
  ├─ 3. _get_agent_llm()
  │      → 从 .env 读取 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
  │      → 创建 OpenHands LLM 实例 (如 deepseek/deepseek-chat)
  │
  ├─ 4. run_student_agent(request, llm=真实LLM)
  │      → Agent 检测到 turn_context 存在 → 走新路径
  │      → from_context(turn_context) → 只注册 game tool
  │
  │      Agent 内部执行:
  │      ├── 直接从 turn_context 读取预检索结果（不调 tool）
  │      ├── LLM 调用 1: 基于检索上下文生成自然语言回答
  │      ├── LLM 调用 2: 决定下一步教学动作 (next_action)
  │      └── 若 next_action=trigger_game → 调 game tool 出题
  │
  │      → 返回 StudentAgentResponse
  │
  ├─ 5. 持久化:
  │      → 写入 qa_records 表 (含 next_action, reason, matched/target 等新字段)
  │      → SessionService.update_position() → 更新 qa_sessions 位置
  │      → ConversationService.append_turn() → 持久化对话轮次
  │
  └─ 6. 返回 {answerId, answerContent, answerType, relatedKnowledge,
              suggestions, understandingLevel, questionType, nextAction,
              reason, matchedSectionId, matchedPage, targetSectionId, targetPage}
```

**关联数据库表**：`qa_sessions`、`qa_records`、`lessons`、`scripts`、`knowledge_bases`

---

### 5.2 语音提问识别

将学生语音提问转换为文字，用于后续问答处理。

- **接口地址**：`POST /api/v1/qa/voiceToText`
- **当前状态**：预留接口框架，ASR 服务待接入

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `voiceUrl` | String | 是 | 语音文件 URL | `"http://xxx.com/voice/123.wav"` |
| `voiceDuration` | Integer | 否 | 语音时长（秒） | `10` |
| `language` | String | 否 | 语言类型（默认 `"zh-CN"`） | `"zh-CN"` / `"en-US"` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据

```json
{
    "code": 200,
    "msg": "语音识别成功",
    "data": {
        "text": "平面假设为什么能简化梁弯曲问题？",
        "confidence": 0.98,
        "timestamp": "2024-05-20 10:05:00"
    },
    "requestId": "req20240520005"
}
```

#### 实现逻辑

```
1. qa_service.voice_to_text(voice_url, language)
   → 当前为 Placeholder 实现
   → 接入 ASR 服务后：下载音频 → 调用 ASR API → 返回识别结果
2. 返回 {text, confidence, timestamp}
```

---

## 七、模块三：学习进度智能适配（`/api/v1/progress/*`）

> **路由文件**：`src/api/routers/progress.py`  
> **服务层**：`src/api/services/progress_service.py`  
> **决策逻辑**：内联规则引擎（与 `StudentOpenHandsAgent` 决策逻辑一致）

### 6.1 学习进度追踪

记录学生学习进度、问答交互记录，为适配调整提供数据支撑。

- **接口地址**：`POST /api/v1/progress/track`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `schoolId` | String | 是 | 学校 ID | `"sch10001"` |
| `userId` | String | 是 | 学生学号 | `"stu20001"` |
| `courseId` | String | 是 | 课程 ID | `"cou30001"` |
| `lessonId` | String | 是 | 智课 ID | `"lesson20240520001"` |
| `currentSectionId` | String | 是 | 当前学习章节 ID | `"sec002"` |
| `progressPercent` | Float | 是 | 章节学习进度（0-100） | `60.5` |
| `lastOperateTime` | String | 是 | 最后操作时间 | `"2024-05-20 10:10:00"` |
| `qaRecordId` | String | 否 | 最近问答记录 ID | `"ans20240520001"` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据

```json
{
    "code": 200,
    "msg": "进度追踪成功",
    "data": {
        "trackId": "track20240520001",
        "totalProgress": 45.2,
        "nextSectionSuggest": "sec003"
    },
    "requestId": "req20240520006"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 查询 learning_progress 表：
  │      WHERE user_id = ? AND lesson_id = ?
  │      → 若已存在 → 更新记录
  │      → 若不存在 → 生成 trackId, 创建新记录
  │
  ├─ 2. _compute_total_progress(db, userId, lessonId, progressPercent)
  │      → 从 lessons 表读取 structured_content
  │      → 统计总章节数 total_sections
  │      → 查询已完成章节数 (progress_percent >= 100)
  │      → totalProgress = (已完成数/总数)×100 + 当前进度/总数
  │      → 上限 100.0
  │
  ├─ 3. _suggest_next_section(db, lessonId, currentSectionId)
  │      → 遍历 structured_content.sections
  │      → 找到当前章节位置
  │      → 返回下一章节的 section_id
  │
  └─ 4. 返回 {trackId, totalProgress, nextSectionSuggest}
```

**关联数据库表**：`learning_progress`、`lessons`

---

### 6.2 学习节奏调整

基于学生理解程度与学习进度，调整后续讲授节奏。

- **接口地址**：`POST /api/v1/progress/adjust`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `userId` | String | 是 | 学生学号 | `"stu20001"` |
| `lessonId` | String | 是 | 智课 ID | `"lesson20240520001"` |
| `currentSectionId` | String | 是 | 当前章节 ID | `"sec002"` |
| `understandingLevel` | String | 是 | 理解程度 | `"none"` / `"partial"` / `"full"` |
| `qaRecordId` | String | 是 | 问答记录 ID | `"ans20240520001"` |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

#### 返回数据

```json
{
    "code": 200,
    "msg": "节奏调整成功",
    "data": {
        "adjustPlan": {
            "continueSectionId": "sec002",
            "adjustType": "supplement",
            "supplementContent": {
                "content": "让我们回顾一下本节的核心要点：平面假设核心内涵、变形前后截面特性。",
                "duration": 30,
                "relatedExample": "工程中常见的简支梁弯曲问题"
            },
            "nextSections": [
                {
                    "sectionId": "sec002",
                    "adjustedDuration": 75,
                    "isKeyPointStrengthen": true
                },
                {
                    "sectionId": "sec003",
                    "adjustedDuration": 40,
                    "isKeyPointStrengthen": false
                }
            ]
        }
    },
    "requestId": "req20240520007"
}
```

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 规则决策 _decide_next_action(understandingLevel):
  │      → understandingLevel == "none"    → "reteach_slowly"
  │      → understandingLevel == "partial" → "supplement_then_resume"
  │      → understandingLevel == "full"    → "resume"
  │      (与 StudentOpenHandsAgent._decide_next_action_rule 逻辑一致)
  │
  ├─ 2. 确定 adjustType:
  │      understandingLevel == "full"        → "accelerate" (加速后续内容)
  │      next_action == "resume"             → "normal"     (正常续讲)
  │      next_action == "supplement_*"       → "supplement"  (补充讲解)
  │      next_action == "reteach_slowly"     → "supplement"  (重新慢讲)
  │      next_action == "trigger_game"       → "supplement"  (互动巩固)
  │
  ├─ 3. 若 adjustType == "supplement":
  │      _build_supplement(db, lessonId, sectionId, understandingLevel)
  │      → 从 lessons.structured_content 提取当前章节知识点
  │      → 生成补充内容文本
  │      → duration: "none" → 60秒, "partial" → 30秒
  │
  ├─ 4. _build_next_sections(db, lessonId, currentSectionId, understandingLevel)
  │      → 从当前章节开始，取后续最多 3 个章节
  │      → 调整 duration: "none"→90s, "partial"→75s, "full"→40s
  │      → 设置 isKeyPointStrengthen: level != "full"
  │
  ├─ 5. 写入 adjust_records 表
  │
  └─ 6. 返回 {adjustPlan: {continueSectionId, adjustType,
                            supplementContent, nextSections}}
```

**关联数据库表**：`adjust_records`、`lessons`

---

## 八、模块四：平台对接预留（`/api/v1/platform/*`）

> **路由文件**：`src/api/routers/platform.py`  
> **服务层**：`src/api/services/platform_service.py`

### 7.1 课程信息同步

与外部教育平台同步课程基础信息，支持智课关联课程体系。

- **接口地址**：`POST /api/v1/platform/syncCourse`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `platformId` | String | 是 | 外部平台 ID | `"plat001"` |
| `courseInfo` | Object | 是 | 课程信息 | 详见下方 |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

**courseInfo 结构**：

```json
{
    "courseId": "plat_cou001",
    "courseName": "材料力学（上册）",
    "schoolId": "sch10001",
    "schoolName": "某某大学",
    "teacherInfo": [{"teacherId": "plat_tea001", "teacherName": "张教授"}],
    "term": "20242",
    "credit": 3.0,
    "period": 48,
    "courseCover": "http://xxx.com/course/cover/001.jpg"
}
```

#### 返回数据

```json
{
    "code": 200,
    "msg": "课程同步成功",
    "data": {
        "internalCourseId": "cou30001",
        "syncStatus": "success",
        "syncTime": "2024-05-20 11:00:00"
    },
    "requestId": "req20240520008"
}
```

#### 实现逻辑

```
1. 以 (platformId, courseInfo.courseId) 作为联合标识
   查询 courses 表是否已存在
2. 若已存在 → 更新课程信息字段
   若不存在 → 生成 internalCourseId (UUID 前缀 "cou"), 创建记录
3. teacherInfo 序列化为 JSON 存储
4. 返回 {internalCourseId, syncStatus, syncTime}
```

**关联数据库表**：`courses`

---

### 7.2 用户信息同步

同步外部平台用户信息（教师/学生），支持权限校验与身份识别。

- **接口地址**：`POST /api/v1/platform/syncUser`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `platformId` | String | 是 | 外部平台 ID | `"plat001"` |
| `userInfo` | Object | 是 | 用户信息 | 详见下方 |
| `enc` | String | 是 | 签名信息 | |
| `time` | String | 是 | 当前时间 | |

**userInfo 结构**：

```json
{
    "userId": "plat_stu001",
    "userName": "李四",
    "role": "student",
    "schoolId": "sch10001",
    "relatedCourseIds": ["plat_cou001"],
    "contactInfo": {"phone": "13800138000", "email": "lisi@xxx.com"}
}
```

#### 返回数据

```json
{
    "code": 200,
    "msg": "用户同步成功",
    "data": {
        "internalUserId": "stu20001",
        "syncStatus": "success",
        "authToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "requestId": "req20240520009"
}
```

#### 实现逻辑

```
1. 以 (platformId, userInfo.userId) 作为联合标识
   查询 users 表是否已存在
2. 若已存在 → 更新用户信息字段, 返回原有 authToken
   若不存在 → 生成 internalUserId (UUID 前缀 "usr")
              → secrets.token_urlsafe(64) 生成 authToken
              → 创建记录
3. contactInfo 中的 phone, email 分别存入独立字段
4. relatedCourseIds 序列化为 JSON 存储
5. 返回 {internalUserId, syncStatus, authToken}
```

**关联数据库表**：`users`

---

## 八-b、知识库内部管理接口（`/internal/kb/*`）

> **路由文件**：`src/api/routers/knowledge_base.py`  
> **服务层**：`src/services/knowledge_base/kb_service.py`、`src/services/knowledge_base/ingestion_pipeline.py`  
> **注意**：这些接口不属于对外开放 API，挂载在 `/internal` 前缀下，无需签名验证。

### 8b.1 列出所有知识库

- **接口地址**：`GET /internal/kb/list`

#### 返回数据

```json
{
    "code": 200,
    "msg": "查询成功",
    "data": [
        {
            "kbId": "kb_fbe1482ac4aa",
            "courseId": "cou30001",
            "kbName": "材料力学课程知识库",
            "status": "ready",
            "chunkCount": 180,
            "sourceCount": 2
        }
    ],
    "requestId": "req..."
}
```

### 8b.2 查询知识库详情

- **接口地址**：`GET /internal/kb/status/{kb_id}`

#### 返回数据

```json
{
    "code": 200,
    "msg": "查询成功",
    "data": {
        "kbId": "kb_fbe1482ac4aa",
        "courseId": "cou30001",
        "kbName": "材料力学课程知识库",
        "status": "ready",
        "indexBackend": "faiss",
        "indexPath": "data/rag_indices/kb/kb_fbe1482ac4aa",
        "chunkCount": 180,
        "sourceCount": 2,
        "sources": [
            {
                "kbSourceId": "kbs_xxx",
                "sourceKind": "lesson",
                "lessonId": "lesson20240520001",
                "status": "pending"
            }
        ]
    }
}
```

### 8b.3 创建知识库

- **接口地址**：`POST /internal/kb/create`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `courseId` | String | 是 | 课程 ID | `"cou30001"` |
| `kbName` | String | 否 | 知识库名称 | `"材料力学知识库"` |
| `indexBackend` | String | 否 | 索引后端（默认 `faiss`） | `"faiss"` / `"numpy"` |

#### 返回数据

```json
{
    "code": 200,
    "msg": "知识库创建成功",
    "data": {
        "kbId": "kb_fbe1482ac4aa",
        "courseid": "cou30001",
        "kbName": "材料力学知识库",
        "status": "draft"
    }
}
```

### 8b.4 添加来源到知识库

- **接口地址**：`POST /internal/kb/addSources`

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `kbId` | String | 是 | 知识库 ID | `"kb_fbe1482ac4aa"` |
| `lessonIds` | Array\<String\> | 是 | 智课 ID 列表 | `["lesson20240520001"]` |

### 8b.5 构建知识库索引

- **接口地址**：`POST /internal/kb/build`

触发离线 ingestion pipeline：将所有来源 lesson 的 structured_content 进行 chunk → embed → FAISS 索引构建。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `kbId` | String | 是 | 知识库 ID | `"kb_fbe1482ac4aa"` |
| `lessonIds` | Array\<String\> | 否 | 指定 lesson（为空则用已添加的来源） | `["lesson20240520001"]` |

#### 实现逻辑

```
请求到达
  │
  ├─ 1. 确定 lesson 列表（参数 > 已添加来源 > 课程下所有 lesson）
  │
  ├─ 2. KBIngestionPipeline.run(lesson_ids):
  │      ├── 遍历每个 lesson → 从 DB 读 structured_content
  │      ├── ChunkBuilder → 切分为 ~420 字的 chunk
  │      ├── Embedder → 向量化（远程 API 或 fallback 本地哈希）
  │      ├── HybridRetriever → 构建 FAISS + BM25 索引
  │      ├── save_to_disk(data/rag_indices/kb/{kb_id}/)
  │      ├── 写入 knowledge_chunks 表（chunk 元数据）
  │      └── 更新 knowledge_bases 表 (status=ready, chunk_count, index_path)
  │
  └─ 3. 返回 {kbId, indexPath, lessonCount}
```

**关联数据库表**：`knowledge_bases`、`knowledge_base_sources`、`knowledge_chunks`、`lessons`

---

## 九、系统接口

### 8.1 健康检查

- **接口地址**：`GET /health`
- **无需签名验证**

#### 返回数据

```json
{
    "status": "ok",
    "service": "ChaoXingAgent AI 互动智课服务系统"
}
```

---

## 十、数据库设计

### 9.1 数据库配置

- **数据库**：MySQL 8.0+
- **字符集**：`utf8mb4`（排序规则 `utf8mb4_unicode_ci`）
- **存储引擎**：InnoDB（支持事务）
- **连接池**：SQLAlchemy（`pool_size=10`，`max_overflow=20`，`pool_recycle=1800s`）

### 9.2 表结构总览

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `users` | 用户表 | user_id, platform_user_id, role, auth_token |
| `courses` | 课程表 | course_id, platform_course_id, course_name |
| `parse_tasks` | 解析任务表 | parse_id, file_url, task_status, structure_preview |
| `scripts` | 脚本表 | script_id, parse_id, script_structure, task_status |
| `audio_tasks` | 音频任务表 | audio_id, script_id, audio_url, task_status |
| `lessons` | 智课表 | lesson_id, course_id, **knowledge_base_id**, structured_content, **content_hash** |
| `qa_sessions` | 问答会话表 | session_id, user_id, lesson_id, **current_section_id**, **current_page**, **progress_percent**, **last_action** |
| `qa_records` | 问答记录表 | answer_id, session_id, question_content, answer_content, **next_action**, **reason**, **matched_section_id**, **target_section_id** |
| `learning_progress` | 学习进度表 | track_id, user_id, lesson_id, progress_percent |
| `adjust_records` | 节奏调整表 | adjust_id, understanding_level, adjust_type |
| `knowledge_bases` | **知识库表** (v1.2 新增) | kb_id, course_id, status, index_path, chunk_count |
| `knowledge_base_sources` | **知识库来源表** (v1.2 新增) | kb_source_id, kb_id, lesson_id, source_kind |
| `knowledge_chunks` | **Chunk 元数据表** (v1.2 新增) | chunk_id, kb_id, lesson_id, text, section_id, page |

### 9.3 核心表 ER 关系

```
courses  1──N  lessons ──── knowledge_bases
                 │                │
          ┌──────┼──────┐   knowledge_base_sources
          │      │      │         │
     parse_tasks │   scripts  knowledge_chunks
                 │      │
                 │   audio_tasks
                 │
          qa_sessions ── qa_records
                 │
       learning_progress ── adjust_records
```

### 9.4 详细字段定义

表模型定义文件：`src/api/models/tables.py`

#### users 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO | 自增主键 |
| user_id | VARCHAR(64) | UNIQUE, INDEX | 系统内部用户 ID |
| platform_user_id | VARCHAR(128) | | 外部平台用户 ID |
| platform_id | VARCHAR(64) | | 外部平台标识 |
| user_name | VARCHAR(128) | | 用户姓名 |
| role | VARCHAR(16) | | 角色：student / teacher |
| school_id | VARCHAR(64) | | 学校 ID |
| email | VARCHAR(256) | | 邮箱 |
| phone | VARCHAR(32) | | 手机号 |
| auth_token | TEXT | | 身份验证令牌 |
| related_course_ids | TEXT | | 关联课程 ID 列表 (JSON) |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | ON UPDATE NOW | 更新时间 |

#### parse_tasks 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO | 自增主键 |
| parse_id | VARCHAR(64) | UNIQUE, INDEX | 解析任务 ID |
| school_id | VARCHAR(64) | | 学校 ID |
| user_id | VARCHAR(64) | INDEX | 发起用户 ID |
| course_id | VARCHAR(64) | INDEX | 课程 ID |
| file_type | VARCHAR(16) | | 文件类型：ppt / pdf |
| file_url | VARCHAR(1024) | | 文件 URL 或本地路径 |
| file_name | VARCHAR(512) | | 文件名 |
| file_size | INT | | 文件大小（字节） |
| page_count | INT | | 页数 |
| is_extract_key_point | BOOLEAN | DEFAULT TRUE | 是否提取重点 |
| task_status | VARCHAR(16) | | processing / completed / failed |
| structure_preview | LONGTEXT | | 知识点结构预览 (JSON) |
| parser_output | LONGTEXT | | 完整解析输出 (JSON) |
| error_message | TEXT | | 错误信息 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | ON UPDATE NOW | 更新时间 |

#### scripts 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO | 自增主键 |
| script_id | VARCHAR(64) | UNIQUE, INDEX | 脚本 ID |
| parse_id | VARCHAR(64) | INDEX | 关联解析任务 ID |
| lesson_id | VARCHAR(64) | INDEX | 关联智课 ID |
| teaching_style | VARCHAR(32) | | standard / detailed / concise |
| speech_speed | VARCHAR(16) | | slow / normal / fast |
| custom_opening | TEXT | | 自定义开场白 |
| script_structure | LONGTEXT | | 脚本结构 (JSON) |
| generate_output | LONGTEXT | | 完整生成输出 (JSON) |
| task_status | VARCHAR(16) | | processing / completed / failed |
| error_message | TEXT | | 错误信息 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | ON UPDATE NOW | 更新时间 |

#### qa_records 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO | 自增主键 |
| answer_id | VARCHAR(64) | UNIQUE, INDEX | 回答 ID |
| session_id | VARCHAR(64) | INDEX | 所属会话 ID |
| user_id | VARCHAR(64) | INDEX | 学生用户 ID |
| course_id | VARCHAR(64) | | 课程 ID |
| lesson_id | VARCHAR(64) | | 智课 ID |
| question_type | VARCHAR(8) | | text / voice |
| **student_question_type** | VARCHAR(32) | | **v1.2** 语义分类：definition/reasoning/.../chitchat/unknown |
| question_content | TEXT | | 提问内容 |
| current_section_id | VARCHAR(64) | | 提问时所在章节 ID |
| **current_page** | INT | | **v1.2** 提问时所在页码 |
| **current_script_block_id** | VARCHAR(64) | | **v1.2** 提问时所在讲稿块 ID |
| answer_content | TEXT | | 系统回答 |
| answer_type | VARCHAR(16) | | text / mixed |
| related_knowledge | TEXT | | 关联知识点 (JSON) |
| suggestions | TEXT | | 追问建议 (JSON) |
| **references_json** | LONGTEXT | | **v1.2** 检索引用 (JSON) |
| understanding_level | VARCHAR(16) | | full / partial / none |
| **next_action** | VARCHAR(32) | | **v1.2** 下一步教学动作 |
| **reason** | TEXT | | **v1.2** 动作原因 |
| **matched_section_id** | VARCHAR(64) | | **v1.2** 主命中章节 ID |
| **matched_page** | INT | | **v1.2** 主命中页码 |
| **target_section_id** | VARCHAR(64) | | **v1.2** 目标章节 ID |
| **target_page** | INT | | **v1.2** 目标页码 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

#### learning_progress 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO | 自增主键 |
| track_id | VARCHAR(64) | UNIQUE, INDEX | 追踪记录 ID |
| school_id | VARCHAR(64) | | 学校 ID |
| user_id | VARCHAR(64) | INDEX | 学生用户 ID |
| course_id | VARCHAR(64) | | 课程 ID |
| lesson_id | VARCHAR(64) | INDEX | 智课 ID |
| current_section_id | VARCHAR(64) | | 当前章节 ID |
| progress_percent | FLOAT | | 章节学习进度 (0-100) |
| total_progress | FLOAT | | 智课总学习进度 (0-100) |
| next_section_suggest | VARCHAR(64) | | 建议后续学习章节 |
| last_operate_time | VARCHAR(32) | | 最后操作时间 |
| qa_record_id | VARCHAR(64) | | 最近问答记录 ID |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | ON UPDATE NOW | 更新时间 |

---

## 十一、架构与调用流程

### 10.1 系统分层架构

```
┌─────────────────────────────────────────────────────┐
│                    客户端 (Web / 移动端)               │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/JSON
┌───────────────────────▼─────────────────────────────┐
│  FastAPI Application (src/api/app.py)                │
│  ├─ CORSMiddleware          (跨域处理)                │
│  ├─ SignatureVerifyMiddleware (MD5 签名验证)           │
│  ├─ Exception Handlers       (全局异常处理)            │
│  └─ OpenAPI/Swagger          (自动文档生成)            │
├─────────────────────────────────────────────────────┤
│  Routers (src/api/routers/)                          │
│  ├─ lesson.py          (/api/v1/lesson/*)  11 端点   │
│  ├─ qa.py              (/api/v1/qa/*)      2 端点    │
│  ├─ progress.py        (/api/v1/progress/*) 2 端点   │
│  ├─ platform.py        (/api/v1/platform/*) 2 端点   │
│  └─ knowledge_base.py  (/internal/kb/*)    5 端点    │
├─────────────────────────────────────────────────────┤
│  Services (src/api/services/ + src/services/)        │
│  ├─ lesson_service.py     (解析/生成/渲染/编辑)       │
│  ├─ qa_service.py         (问答编排 + LLM 创建)      │
│  ├─ progress_service.py   (进度追踪/节奏调整)         │
│  ├─ platform_service.py   (课程/用户同步)             │
│  ├─ student/context_builder.py  (Pre-RAG 上下文组装) │
│  ├─ student/session_service.py  (MySQL session 管理) │
│  ├─ student/conversation_service.py (对话持久化)     │
│  ├─ student/retrieval_service.py    (KB/即时检索)     │
│  ├─ knowledge_base/kb_service.py    (知识库 CRUD)    │
│  └─ knowledge_base/ingestion_pipeline.py (离线建库)  │
├─────────────────────────────────────────────────────┤
│  AI Agents (src/agents/)                             │
│  ├─ file_parser.py      (LLM 课件解析)                │
│  ├─ generate.py         (LLM 脚本生成)                │
│  └─ student/agent.py    (OpenHands 学生问答 Agent)     │
│     ├─ 保留工具: game（其他 4 个已移至后端 service）    │
│     ├─ LLM 调用 1: 基于检索上下文生成回答              │
│     └─ LLM 调用 2: 决定 next_action 教学决策           │
├─────────────────────────────────────────────────────┤
│  Data Layer                                          │
│  ├─ SQLAlchemy ORM  (src/api/models/)                │
│  ├─ MySQL 8.0       (13 张业务表)                     │
│  ├─ File Storage     (data/uploads/, data/audio/)    │
│  ├─ KB Index         (data/rag_indices/kb/*)         │
│  └─ Conversations    (data/conversations/*)          │
└─────────────────────────────────────────────────────┘
```

### 10.2 核心业务调用流程

```
教师端                                              学生端
  │                                                   │
  │  ① 上传课件                                        │
  ├──→ POST /lesson/parse ──────────────────┐          │
  │                                         │          │
  │  ② 后台异步解析 (file_parser Agent)      │          │
  │    ┌────────────────────────────────────┘          │
  │    │  PPT/PDF → 文本提取 → LLM 解析                 │
  │    │  → 知识点识别 → 结构化输出                      │
  │    └──→ parse_tasks 表更新                          │
  │                                                   │
  │  ③ 查询解析状态                                     │
  ├──→ POST /lesson/parseStatus                        │
  │                                                   │
  │  ④ 生成讲授脚本                                     │
  ├──→ POST /lesson/generateScript ─────────┐          │
  │                                         │          │
  │  ⑤ 后台异步生成 (generate Agent)         │          │
  │    ┌────────────────────────────────────┘          │
  │    │  结构化内容 → LLM 生成脚本                      │
  │    │  → 开场白 + 讲解 + 过渡语 + 重点               │
  │    └──→ scripts 表更新                              │
  │                                                   │
  │  ⑥ 编辑脚本 (可选)                                  │
  ├──→ POST /lesson/editScript                         │
  │                                                   │
  │  ⑦ 语音合成 (TTS)                                   │
  ├──→ POST /lesson/generateAudio                      │
  │                                                   │
  │                                                   │
  │                                  ⑧ 学习智课 & 提问  │
  │                                  ├──→ POST /qa/interact
  │                                  │    → context_builder: session + history + KB检索
  │                                  │    → StudentOpenHandsAgent (真实 LLM):
  │                                  │      LLM 基于检索上下文生成回答
  │                                  │      LLM 决定 next_action 教学动作
  │                                  │    → 返回 nextAction + 追问建议
  │                                  │                │
  │                                  │ ⑨ 上报学习进度  │
  │                                  ├──→ POST /progress/track
  │                                  │    → 计算总进度
  │                                  │    → 推荐下一章节
  │                                  │                │
  │                                  │ ⑩ 节奏调整      │
  │                                  └──→ POST /progress/adjust
  │                                       → 规则决策 (与 Agent 一致)
  │                                       → 补充/加速/正常/互动
  │                                       → 调整后续章节时长
```

---

## 十二、配置说明

配置通过环境变量或项目根目录 `.env` 文件加载：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PROJECT_NAME` | `ChaoXingAgent AI 互动智课服务系统` | 项目名称 |
| `API_V1_PREFIX` | `/api/v1` | API 版本前缀 |
| `DEBUG` | `false` | 调试模式（true 时跳过签名验证） |
| `DATABASE_URL` | `mysql+pymysql://root:root@127.0.0.1:3306/chaoxing?charset=utf8mb4` | 数据库连接 |
| `DB_POOL_SIZE` | `10` | 连接池大小 |
| `DB_MAX_OVERFLOW` | `20` | 最大溢出连接数 |
| `DB_POOL_RECYCLE` | `1800` | 连接回收时间（秒） |
| `STATIC_KEY` | `chaoxing_default_static_key` | 签名密钥 |
| `SIGNATURE_TIMEOUT_SECONDS` | `300` | 签名有效窗口（秒） |
| `UPLOAD_DIR` | `{项目根}/data/uploads` | 课件上传目录 |
| `AUDIO_DIR` | `{项目根}/data/audio` | 音频存储目录 |
| `RENDER_DIR` | `{项目根}/data/renders` | 渲染 PPT 存储目录 |
| `LLM_ENV_PATH` | *(无)* | LLM 配置 .env 文件路径 |
| `CORS_ORIGINS` | `["*"]` | CORS 允许的来源 |

---

## 十三、项目源码结构

```
src/api/
├── app.py                  # FastAPI 应用入口 + 全局异常 + Tag 元数据
├── config.py               # pydantic-settings 配置管理
├── deps.py                 # 依赖注入 (generate_request_id, generate_id)
├── middleware.py            # MD5 签名验证中间件
├── response_models.py       # 全部 Pydantic 响应模型 (ApiResponse[T])
├── models/
│   ├── database.py          # SQLAlchemy engine / SessionLocal / init_db
│   └── tables.py            # 13 张表的 ORM 模型定义
├── routers/
│   ├── lesson.py            # 智课生成模块 (11 endpoints)
│   ├── qa.py                # 实时问答模块 (2 endpoints)
│   ├── progress.py          # 学习进度模块 (2 endpoints)
│   ├── platform.py          # 平台对接模块 (2 endpoints)
│   └── knowledge_base.py   # 知识库内部管理 (5 endpoints)   ← v1.2 新增
└── services/
    ├── lesson_service.py    # 解析/生成/音频/编辑 业务逻辑
    ├── qa_service.py        # 问答编排 + LLM 创建 业务逻辑
    ├── progress_service.py  # 进度追踪/节奏调整 业务逻辑
    └── platform_service.py  # 课程/用户同步 业务逻辑

src/services/                                          ← v1.2 新增
├── student/
│   ├── context_builder.py   # Pre-RAG 上下文组装（核心编排器）
│   ├── session_service.py   # MySQL session 读写
│   ├── conversation_service.py # 对话历史持久化
│   └── retrieval_service.py # KB / 即时索引混合检索
└── knowledge_base/
    ├── kb_service.py        # 知识库 CRUD
    └── ingestion_pipeline.py # 离线 chunk→embed→FAISS 建库
```

---

## 十四、启动与测试

### 13.1 开发模式启动

```bash
# 跳过签名验证
DEBUG=true uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### 13.2 查看 API 文档

- **Swagger UI**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`
- **OpenAPI JSON**：`http://localhost:8000/openapi.json`

### 13.3 接口测试示例

```bash
# 健康检查
curl http://localhost:8000/health

# 课件解析（DEBUG 模式，无需签名）
curl -X POST http://localhost:8000/api/v1/lesson/parse \
  -H "Content-Type: application/json" \
  -d '{
    "schoolId": "sch10001",
    "userId": "tea20001",
    "courseId": "cou30001",
    "fileType": "pdf",
    "fileUrl": "/path/to/courseware.pdf",
    "isExtractKeyPoint": true
  }'

# 问答交互
curl -X POST http://localhost:8000/api/v1/qa/interact \
  -H "Content-Type: application/json" \
  -d '{
    "schoolId": "sch10001",
    "userId": "stu20001",
    "courseId": "cou30001",
    "lessonId": "lesson20240520001",
    "sessionId": "ses001",
    "questionType": "text",
    "questionContent": "什么是平面假设？",
    "currentSectionId": "sec002"
  }'

# 学习进度追踪
curl -X POST http://localhost:8000/api/v1/progress/track \
  -H "Content-Type: application/json" \
  -d '{
    "schoolId": "sch10001",
    "userId": "stu20001",
    "courseId": "cou30001",
    "lessonId": "lesson20240520001",
    "currentSectionId": "sec002",
    "progressPercent": 60.5,
    "lastOperateTime": "2024-05-20 10:10:00"
  }'
```
