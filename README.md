# 智学工坊 — AI 个性化学习平台

> 基于大模型的工科生个性化学习资源生成与多智能体学习辅助系统

## 快速启动

```bash
# 1. 安装后端依赖
uv sync

# 2. 启动后端（终端 1）
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8001

# 3. 启动前端（终端 2）
cd frontend
npm install
npm run dev
```

- 前端：http://127.0.0.1:3000
- API 文档：http://127.0.0.1:8001/docs

## 默认账号

| 角色 | 账号 | 密码 |
|------|------|------|
| 管理员 | admin | admin123 |
| 学生 | 注册新账号 | 自行设置 |

## 核心功能

- **六维学生画像**：AI 根据自然语言对话生成六维画像（雷达图可视化）
- **个性化学习路径**：基于画像自动规划学习路线和阶段目标
- **智能资源生成**：按需生成文档、PPT、思维导图、练习题等资源
- **资源中心**：40 条种子数据，支持筛选搜索
- **AI 助教**：问答、选中文字添加、截图提问
- **学习行为管理**：事件上报、掌握度追踪、错题本/收藏

## 技术栈

- **前端**：Vue 3 + Vite 7 + Element Plus + Pinia + ECharts
- **后端**：FastAPI + SQLAlchemy 2 + PostgreSQL（NeonDB 云端）
- **AI**：DeepSeek API（支持 Mock 降级）
- **认证**：JWT（python-jose + PBKDF2）

## 文档

详细文档见 [`docs/README.md`](docs/README.md)，开发计划见 [`plan/plan.md`](plan/plan.md)。
