# 智学工坊 — AI 个性化学习平台

> 基于大模型的工科生个性化学习资源生成与多智能体学习辅助系统

---

## 一、项目概述

### 1.1 项目定位

智学工坊是一个面向计算机、软件工程、人工智能等信息类工科学生的个性化学习平台。系统以**动态学生画像**为核心，以**个性化学习路径**为主线，以**资源生成、智能助手、学习行为感知**为支撑，形成持续更新的个性化学习闭环。

### 1.2 核心闭环

```
新用户 → 初始化画像 → 六维画像生成 → 个性化路径 → 
平台资源推荐 → 资源生成 → 学习行为采集 → 
画像更新 → 路径动态调整
```

### 1.3 技术栈

| 层次 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 3.5 + 7.3 |
| UI 组件库 | Element Plus | 2.13 |
| 状态管理 | Pinia | 3.0 |
| 路由 | Vue Router 4 | 4.6 |
| 可视化 | ECharts 5 | 5.5 |
| Markdown | markdown-it | 14.1 |
| 截图 | html2canvas | 1.4 |
| 后端框架 | FastAPI + Uvicorn | 0.115 + 0.34 |
| ORM | SQLAlchemy 2 | 2.0 |
| 数据库 | PostgreSQL（NeonDB 云端） | 16 |
| 认证 | JWT（python-jose） | 3.3 |
| AI 引擎 | DeepSeek API（可选 Mock 降级） | deepseek-chat |
| HTTP 客户端 | httpx（异步） | 0.27 |

---

## 二、快速启动

### 2.1 环境要求

- Python >= 3.13, < 3.14
- Node.js >= 20
- uv（Python 包管理器）
- npm

### 2.2 启动后端

```bash
cd D:\A3
uv sync                            # 安装 Python 依赖
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8001
```

### 2.3 启动前端

```bash
cd D:\A3\frontend
npm install                         # 安装前端依赖
npm run dev                         # 启动开发服务器（默认 127.0.0.1:3000）
```

### 2.4 访问地址

| 服务 | 地址 |
|------|------|
| 前端页面 | http://127.0.0.1:3000 |
| API 文档 | http://127.0.0.1:8001/docs |
| 后端健康检查 | http://127.0.0.1:8001/health |

### 2.5 默认账号

| 角色 | 账号 | 密码 |
|------|------|------|
| 管理员 | admin | admin123 |
| 学生 | 注册新账号 | 自行设置 |

---

## 三、项目目录结构

```
D:\A3\
├── .env                          # 环境变量（数据库、JWT、AI 配置）
├── pyproject.toml                # 项目依赖配置
├── ruff.toml                     # 代码规范配置
├── start.bat                     # Windows 一键启动脚本
├── stop.bat                      # Windows 停止脚本
│
├── src/                          # 后端代码
│   ├── main.py                   # FastAPI 应用入口
│   ├── core/                     # 核心基础设施
│   │   ├── config.py             # Pydantic Settings 配置
│   │   ├── database.py           # SQLAlchemy 引擎和会话管理
│   │   ├── security.py           # JWT 鉴权和密码哈希
│   │   └── deps.py               # FastAPI 依赖注入
│   ├── models/                   # 数据库模型（10 张表）
│   │   ├── user.py               # 用户模型
│   │   ├── profile.py            # 学生画像模型
│   │   ├── learning_path.py      # 学习路径模型
│   │   ├── resource.py           # 资源和生成资源模型
│   │   ├── event.py              # 学习事件和掌握度模型
│   │   ├── assistant.py          # 助手会话和消息模型
│   │   └── quiz.py               # 答题记录模型
│   ├── schemas/                  # Pydantic 数据模型
│   │   ├── user_schema.py        # 用户认证相关 Schema
│   │   ├── profile_schema.py     # 画像相关 Schema
│   │   ├── path_schema.py        # 路径相关 Schema
│   │   ├── resource_schema.py    # 资源相关 Schema
│   │   └── event_schema.py       # 事件/助手/测验 Schema
│   ├── api/routers/              # API 路由
│   │   ├── auth.py               # 认证路由
│   │   ├── profile.py            # 画像路由
│   │   ├── path.py               # 路径路由
│   │   ├── resource.py           # 资源路由
│   │   ├── generated_resource.py # 生成资源路由
│   │   ├── event.py              # 学习事件路由
│   │   ├── assistant.py          # 智能助手路由
│   │   └── quiz.py               # 练习题路由
│   ├── services/                 # 业务逻辑层
│   │   ├── auth_service.py       # 认证服务
│   │   ├── dify_service.py       # AI 服务（DeepSeek API + Mock）
│   │   ├── profile_service.py    # 画像服务
│   │   ├── path_service.py       # 路径服务
│   │   └── resource_service.py   # 资源服务（含种子数据）
│   └── utils/                    # 工具函数
│       ├── response.py           # 统一响应格式
│       └── llm_client.py         # LLM 客户端（旧版，保留兼容）
│
├── frontend/                     # 前端代码
│   ├── src/
│   │   ├── main.js               # 应用入口
│   │   ├── App.vue               # 根组件 + 全局 CSS 变量
│   │   ├── router/index.js       # 路由定义 + 守卫
│   │   ├── store/                # Pinia 状态管理
│   │   │   ├── userStore.js      # 用户认证状态
│   │   │   ├── profileStore.js   # 画像状态
│   │   │   ├── pathStore.js      # 路径状态
│   │   │   ├── resourceStore.js  # 资源状态
│   │   │   └── assistantStore.js # 助手状态
│   │   ├── api/                  # API 请求封装
│   │   │   ├── auth.js           # 认证 API
│   │   │   ├── profile.js        # 画像 API
│   │   │   ├── path.js           # 路径 API
│   │   │   ├── resource.js       # 资源 API
│   │   │   ├── generatedResource.js
│   │   │   ├── event.js          # 事件 API
│   │   │   ├── assistant.js      # 助手 API
│   │   │   └── quiz.js           # 测验 API
│   │   ├── views/                # 页面组件
│   │   │   ├── Home.vue          # 首页
│   │   │   ├── Login.vue         # 登录/注册
│   │   │   ├── Dashboard.vue     # 工作台
│   │   │   ├── ProfileInit.vue   # 初始化画像（自然对话）
│   │   │   ├── ProfilePage.vue   # 学生画像/学习报告
│   │   │   ├── LearningPath.vue  # 个性化路径
│   │   │   ├── ResourceCenter.vue# 资源中心
│   │   │   ├── ResourceDetail.vue# 资源详情
│   │   │   ├── DocumentReader.vue# 文档阅读
│   │   │   ├── GeneratedResource.vue # 资源生成
│   │   │   ├── SettingsPage.vue  # 设置
│   │   │   ├── WrongBookPage.vue # 错题本
│   │   │   ├── FavoritesPage.vue # 我的收藏
│   │   │   ├── AdminPage.vue     # 管理员中心
│   │   │   ├── VideoLearningPage.vue # 视频学习
│   │   │   └── QuizPracticePage.vue  # 练习题
│   │   └── components/           # 通用组件
│   │       ├── AppSidebar.vue    # 侧边栏导航
│   │       ├── AppHeader.vue     # 顶部栏
│   │       ├── PageLayout.vue    # 页面布局壳
│   │       ├── AssistantPanel.vue # AI 助教面板
│   │       ├── AiRobot3d.vue     # 3D 机器人
│   │       ├── ProfileRadar.vue  # 雷达图
│   │       ├── PathTimeline.vue  # 路径时间轴
│   │       ├── ResourceCard.vue  # 资源卡片
│   │       ├── MarkdownRenderer.vue # Markdown 渲染
│   │       └── StateBlock.vue    # 空/加载/错误状态
│   └── utils/
│       └── request.js            # Axios 封装（拦截器/JWT）
│
├── plan/
│   └── plan.md                   # 项目开发计划书
│
├── PRODUCT.md                    # 产品定义文档
└── README.md                     # 项目说明
```

---

## 四、数据库设计

系统使用 **PostgreSQL（NeonDB 云端）**，包含 10 张业务表：

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `user` | 用户 | id, username, password_hash, role(student/admin) |
| `student_profile` | 学生画像 | user_id, profile_json(JSON), summary, version |
| `learning_path` | 学习路径 | user_id, title, path_json(JSON), status |
| `platform_resource` | 平台资源 | title, type, direction, difficulty, 40 条种子数据 |
| `generated_resource` | 生成资源 | user_id, type, title, content(Markdown) |
| `learning_event` | 学习行为事件 | user_id, event_type, resource_id, event_data |
| `knowledge_mastery` | 知识点掌握度 | user_id, knowledge_point, mastery_score |
| `assistant_conversation` | 助手会话 | user_id, title, context_type |
| `assistant_message` | 助手消息 | conversation_id, role, content |
| `quiz_record` | 答题记录 | user_id, knowledge_point, is_correct |

---

## 五、API 接口

所有接口以 `/api/v1` 为前缀，认证使用 `Bearer JWT`。

### 5.1 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册学生账号 |
| POST | `/auth/login` | 登录获取 JWT |
| GET | `/auth/me` | 获取当前用户信息 |

### 5.2 画像

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/profile/me` | 获取最新画像 |
| POST | `/profile/init` | 初始化画像（对话历史 → 六维画像） |
| GET | `/profile/history` | 画像历史版本 |

### 5.3 学习路径

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/paths` | 路径列表 |
| POST | `/paths/generate` | 生成路径（画像 → 路径） |
| GET | `/paths/{id}` | 路径详情 |
| PUT | `/paths/{id}/status` | 更新路径状态 |

### 5.4 资源中心

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/resources` | 资源列表（筛选/搜索/分页） |
| GET | `/resources/{id}` | 资源详情 |
| POST | `/resources/{id}/view` | 记录查看 |

### 5.5 生成资源

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generated-resources/generate` | 生成资源 |
| GET | `/generated-resources` | 生成历史 |
| GET | `/generated-resources/{id}` | 生成详情 |

### 5.6 智能助手

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/assistant/chat` | 发送消息 |
| GET | `/assistant/conversations` | 会话列表 |
| GET | `/assistant/conversations/{id}/messages` | 会话消息 |

### 5.7 学习事件

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/events` | 上报单条事件 |
| POST | `/events/batch` | 批量上报 |
| GET | `/events/me` | 个人事件 |
| GET | `/events/mastery/me` | 知识点掌握度 |

### 5.8 练习题

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/quiz/generate` | 生成练习题 |
| POST | `/quiz/submit` | 提交答案 |
| GET | `/quiz/records` | 答题记录 |
| GET | `/quiz/wrong` | 错题列表 |

---

## 六、AI 能力说明

### 6.1 AI 引擎架构

系统支持两种 AI 模式，通过 `.env` 中的 `DIFY_MOCK_MODE` 切换：

```env
# Mock 模式（默认，无需网络，返回预置数据）
DIFY_MOCK_MODE=true

# 真实 DeepSeek 模式
DIFY_MOCK_MODE=false
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 6.2 六维学生画像

AI 根据学生的自然语言对话生成六维画像：

| 维度 | 说明 | 评估内容 |
|------|------|---------|
| basic_knowledge | 基础知识掌握度 | 编程语言、数据结构、网络、数据库 |
| engineering_ability | 工程实践能力 | Web 开发、部署、Git、Docker |
| ai_data_ability | AI 与数据能力 | 机器学习、深度学习、大模型、RAG |
| learning_goal | 学习目标与发展方向 | 目标清晰度、就业/考研/竞赛方向 |
| resource_preference | 学习偏好与资源偏好 | 文档/视频/项目偏好、学习风格 |
| learning_behavior | 学习行为与掌握状态 | 学习态度、时间管理、风险标记 |

### 6.3 三个 AI 功能

| 功能 | 输入 | 输出 | 触发时机 |
|------|------|------|---------|
| 画像生成 | 对话历史数组 | 六维 JSON + 自然语言总结 | 初始化画像 |
| 路径规划 | 画像 JSON + 偏好设置 | 阶段化路径（3-5 阶段） | 生成路径 |
| 资源生成 | 类型 + 知识点 + 难度 | Markdown 内容 | 生成资源 |

---

## 七、前端页面

| 页面 | 路由 | 描述 |
|------|------|------|
| 首页 | `/` | 公开页面，Hero + 功能入口 + 推荐资源 + 任务 + 日历 |
| 登录 | `/login` | 登录/注册切换，JWT 持久化 |
| 工作台 | `/dashboard` | 快捷入口 + 今日任务 + 日历 + 进度环 + 雷达图 + 公告 |
| 初始化画像 | `/profile/init` | AI 自然语言对话采集信息，右侧预览卡片 |
| 学生画像 | `/profile` | 雷达图 + 得分条 + 趋势图 + 优势/薄弱标签 + 证据 + 建议 |
| 个性化路径 | `/learning-path` | 目标卡片 + 阶段网格 + 里程碑 + AI 建议 |
| 资源中心 | `/resources` | 筛选/搜索 + 卡片网格（40 条种子数据）|
| 资源详情 | `/resources/:id` | 封面 + 信息 + 简介 + 预览 + 推荐 |
| 文档阅读 | `/resources/:id/read` | 三栏（目录 + 文档 + AI 助教联动）|
| 资源生成 | `/generated-resources` | 类型切换 + 配置 + 生成结果 |
| 错题本 | `/learning-path/wrong-book` | 错题列表 + 统计数据 + 复习建议 |
| 我的收藏 | `/learning-path/favorites` | 收藏资源列表 |
| 设置 | `/settings` | 个人信息 + 学习偏好 + 安全设置 |
| 管理员 | `/admin` | 资源管理 + 用户管理 + Dify 配置 |
| 视频学习 | `/resources/:id/video` | 视频播放页面 |
| 练习题 | `/resources/:id/quiz` | 题目练习与提交 |

---

## 八、种子数据

资源中心预置 **40 条**种子数据，覆盖 4 个方向 7 种类型：

| 类型 | 数量 | 示例 |
|------|------|------|
| 课程 | 9 | Python 基础入门、数据结构与算法、深度学习入门 |
| 文档 | 7 | FastAPI 官方文档、RAG 系统搭建指南、Git 协作 |
| 视频 | 7 | Vue 3 组合式 API、Docker 容器化、PyTorch 入门 |
| PPT | 4 | 机器学习基础概念、Web 安全防护体系 |
| 思维导图 | 3 | Java 知识体系、AI 学习路线图 |
| 题库 | 5 | Python 基础 100 题、SQL 查询挑战 |
| 项目案例 | 5 | 在线考试系统、智能问答机器人 |

难度分布：入门 11 / 中级 14 / 高级 15

---

## 九、系统架构图

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                      │
│  ┌─────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ 页面组件 │ │ Pinia    │ │ Axios + JWT          │  │
│  │ 17 个   │ │ Store ×5 │ │ → 后端 API           │  │
│  └─────────┘ └──────────┘ └──────────────────────┘  │
├─────────────────────────────────────────────────────┤
│              后端 (FastAPI)                          │
│  ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 路由 │ │ 服务层  │ │ AI 服务  │ │ 数据库 ORM   │ │
│  │ ×30  │ │ ×5     │ │ DeepSeek │ │ SQLAlchemy   │ │
│  └──────┘ └────────┘ └──────────┘ └──────────────┘ │
├─────────────────────────────────────────────────────┤
│            PostgreSQL (NeonDB 云端)                  │
│          10 张表 / 40 条种子数据                    │
└─────────────────────────────────────────────────────┘
```

---

## 十、开发规划

按 `plan/plan.md` 分为四个阶段：

| 阶段 | 内容 | 完成状态 |
|------|------|---------|
| **阶段一** | 基础系统 + 核心闭环 MVP（画像→路径→资源） | ✅ 基本完成 |
| **阶段二** | 智能助手与上下文交互（选中文字、截图、图片上传） | ⚠️ 部分完成 |
| **阶段三** | 学习行为感知与主动干预（阅读检测、弹窗出题） | ⏳ 未开始 |
| **阶段四** | 可视化与高级展示（答辩优化） | ⏳ 未开始 |

---

## 十一、环境变量

`.env` 文件位于项目根目录：

```env
# 应用配置
APP_NAME=智学工坊
DEBUG=true

# PostgreSQL
DATABASE_URL=postgresql+psycopg2://user:pass@host/db?sslmode=require

# JWT 认证
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# AI 配置
DIFY_MOCK_MODE=true                    # true=Mock, false=真实 DeepSeek
LLM_API_KEY=sk-your-key                # DeepSeek API Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# 上传
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=20
```

---

## 十二、常见问题

**Q: 启动后页面空白/无数据？**
A: 需要同时启动后端和前端。后端 `uvicorn` 运行在 8001 端口，前端 `npm run dev` 运行在 3000 端口。

**Q: 首次注册后跳转到哪里？**
A: 注册成功自动跳转到 `/profile/init` 初始化画像。登录用户跳转到工作台。

**Q: 管理员如何登录？**
A: 账号 `admin`，密码 `admin123`。登录后侧边栏出现"管理员中心"。

**Q: 如何切换真实 AI？**
A: 修改 `.env` 中 `DIFY_MOCK_MODE=false`，并填写有效的 `LLM_API_KEY`。

**Q: 数据存在哪里？**
A: 所有业务数据存储在 PostgreSQL（NeonDB 云端）。前端设置存储在 localStorage。
