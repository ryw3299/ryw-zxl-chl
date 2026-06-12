# ChaoXingAgent 项目环境配置与启动指南

> 本文档面向**纯新手**，手把手指导你从零配置开发环境并成功启动项目服务。

---

## 目录

1. [项目简介](#1-项目简介)
2. [环境要求总览](#2-环境要求总览)
3. [Step 1：安装 Python](#step-1安装-python)
4. [Step 2：安装 Node.js](#step-2安装-nodejs)
5. [Step 3：安装 MySQL 数据库](#step-3安装-mysql-数据库)
6. [Step 4：安装 LibreOffice（可选）](#step-4安装-libreoffice可选)
7. [Step 5：克隆项目代码](#step-5克隆项目代码)
8. [Step 6：配置 Python 虚拟环境并安装依赖](#step-6配置-python-虚拟环境并安装依赖)
9. [Step 7：配置环境变量（.env 文件）](#step-7配置环境变量env-文件)
10. [Step 8：初始化数据库](#step-8初始化数据库)
11. [Step 9：启动后端服务](#step-9启动后端服务)
12. [Step 10：安装并启动前端](#step-10安装并启动前端)
13. [验证服务是否正常运行](#验证服务是否正常运行)
14. [常见问题排查（FAQ）](#常见问题排查faq)
15. [项目目录结构说明](#项目目录结构说明)

---

## 1. 项目简介

**ChaoXingAgent** 是"基于泛雅平台的 AI 互动智课生成与实时问答系统"。系统能将教师上传的静态课件（PPT/PDF/DOCX 等）自动转化为可交互的智能课程，核心功能包括：

- **智课生成** — 课件解析 → 脚本生成 → PPT 渲染 → 语音合成
- **实时问答** — 文字/语音提问 → 上下文关联解答
- **进度适配** — 学习进度追踪 → 理解程度分析 → 讲授节奏调整

技术栈：
- **后端**：Python + FastAPI + SQLAlchemy + MySQL
- **前端**：Vue 3 + Vite + Axios
- **AI**：DeepSeek 大模型（OpenAI 兼容接口）

---

## 2. 环境要求总览

| 软件 | 最低版本 | 用途 | 是否必须 |
|------|---------|------|---------|
| **Python** | 3.10+ | 后端运行环境 | ✅ 必须 |
| **pip** | 随 Python 安装 | Python 包管理 | ✅ 必须 |
| **Node.js** | 18+ | 前端运行环境 | ✅ 必须 |
| **npm** | 随 Node.js 安装 | 前端包管理 | ✅ 必须 |
| **MySQL** | 8.0+ | 数据库 | ✅ 必须 |
| **Git** | 任意版本 | 代码版本管理 | ✅ 必须 |
| **LibreOffice** | 7.0+ | .ppt 转 .pptx | ⚠️ 可选 |

---

## Step 1：安装 Python

### macOS

推荐使用 Homebrew：

```bash
# 安装 Homebrew（如果还没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python 3.12
brew install python@3.12
```

### Windows

1. 前往 [Python 官网](https://www.python.org/downloads/) 下载 Python 3.12 安装包
2. 运行安装程序，**务必勾选 "Add Python to PATH"**
3. 安装完成后打开命令提示符验证：

```bash
python --version
# 应输出 Python 3.12.x
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

### 验证安装

```bash
python3 --version   # 或 python --version（Windows）
pip3 --version       # 或 pip --version（Windows）
```

---

## Step 2：安装 Node.js

### 推荐方式：使用 nvm（Node Version Manager）

**macOS / Linux：**

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 重新打开终端后安装 Node.js
nvm install 20
nvm use 20
```

**Windows：**

1. 前往 [Node.js 官网](https://nodejs.org/) 下载 LTS 版本安装包
2. 运行安装程序，一路默认即可

### 验证安装

```bash
node --version   # 应输出 v18.x 或 v20.x
npm --version    # 应输出 9.x 或 10.x
```

---

## Step 3：安装 MySQL 数据库

### macOS

```bash
brew install mysql
brew services start mysql

# 设置 root 密码（首次安装后执行）
mysql_secure_installation
```

### Windows

1. 前往 [MySQL 官网](https://dev.mysql.com/downloads/installer/) 下载 MySQL Installer
2. 选择 "Developer Default" 安装
3. 安装过程中设置 root 密码（**请记住这个密码，后面要用**）

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo mysql_secure_installation
```

### 验证安装

```bash
mysql -u root -p
# 输入密码后进入 MySQL 命令行，输入 exit 退出
```

---

## Step 4：安装 LibreOffice（可选）

> 仅当你需要处理 `.ppt`（旧版 PowerPoint）格式文件时才需要安装。如果只处理 `.pptx` 格式，可跳过此步。

### macOS

```bash
brew install --cask libreoffice
```

### Windows

前往 [LibreOffice 官网](https://www.libreoffice.org/download/) 下载安装。

### Linux

```bash
sudo apt install libreoffice
```

---

## Step 5：克隆项目代码

```bash
# 克隆仓库
git clone https://github.com/你的用户名/ChaoXingAgent.git

# 进入项目目录
cd ChaoXingAgent
```

> 如果你已经有项目代码，直接进入项目根目录即可。

---

## Step 6：配置 Python 虚拟环境并安装依赖

### 6.1 创建虚拟环境

```bash
# 在项目根目录下执行
python3 -m venv venv
```

### 6.2 激活虚拟环境

**macOS / Linux：**

```bash
source venv/bin/activate
```

**Windows（CMD）：**

```cmd
venv\Scripts\activate.bat
```

**Windows（PowerShell）：**

```powershell
venv\Scripts\Activate.ps1
```

> 激活成功后，终端提示符前面会出现 `(venv)` 标识。

### 6.3 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 6.4 以开发模式安装项目本身

```bash
pip install -e .
```

> 这一步确保 `src` 包可以被正确导入。如果 `setup.py` 为空，可以跳过此步，改为在启动时确保从项目根目录运行命令。

### 依赖说明

| 包名 | 用途 |
|------|------|
| `fastapi` | Web API 框架 |
| `uvicorn[standard]` | ASGI 服务器，运行 FastAPI |
| `sqlalchemy` | ORM 数据库操作 |
| `pymysql` | MySQL 数据库驱动 |
| `pydantic` / `pydantic-settings` | 数据校验与配置管理 |
| `PyYAML` | YAML 格式 Prompt 文件解析 |
| `PyMuPDF` | PDF 文件解析 |
| `python-pptx` | PPTX 文件解析与渲染 |
| `python-docx` | DOCX 文件解析 |
| `python-multipart` | 文件上传支持 |
| `pytest` | 单元测试框架 |

---

## Step 7：配置环境变量（.env 文件）

在**项目根目录**下创建 `.env` 文件：

```bash
# macOS / Linux
touch .env

# Windows（PowerShell）
New-Item .env
```

将以下内容复制到 `.env` 文件中，并**根据你的实际情况修改**：

```env
# ============================================================
# 数据库配置
# ============================================================
# 格式: mysql+pymysql://用户名:密码@主机地址:端口/数据库名?charset=utf8mb4
# 请将 root:root 替换为你的 MySQL 用户名和密码
DATABASE_URL=mysql+pymysql://root:你的MySQL密码@127.0.0.1:3306/chaoxing?charset=utf8mb4

# 数据库连接池配置（一般无需修改）
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800

# ============================================================
# 调试模式
# ============================================================
# 设为 true 可跳过 API 签名验证，开发阶段建议开启
DEBUG=true

# ============================================================
# LLM 大模型配置（智课生成核心依赖）
# ============================================================
# LLM 服务提供商（默认 deepseek）
LLM_PROVIDER=deepseek

# DeepSeek API 密钥（必填！前往 https://platform.deepseek.com/ 注册获取）
LLM_API_KEY=你的DeepSeek_API_Key

# DeepSeek API 地址（默认值，一般无需修改）
LLM_BASE_URL=https://api.deepseek.com

# 使用的模型名称
LLM_MODEL=deepseek-chat

# LLM 请求超时时间（秒）
LLM_TIMEOUT_SECONDS=60

# LLM 生成温度（0-1，越低越稳定）
LLM_TEMPERATURE=0.2

# LLM 最大输出 token 数
LLM_MAX_TOKENS=4096

# ============================================================
# LLM 并发与重试配置
# ============================================================
LLM_MAX_CONCURRENT=5
LLM_RETRY_ATTEMPTS=3
LLM_RETRY_DELAY_SECONDS=2.0

# ============================================================
# API 签名密钥（生产环境需修改）
# ============================================================
STATIC_KEY=chaoxing_default_static_key
SIGNATURE_TIMEOUT_SECONDS=300

# ============================================================
# CORS 跨域配置
# ============================================================
# 开发阶段允许所有来源，生产环境应限制为前端域名
CORS_ORIGINS=["*"]
```

### ⚠️ 重要说明

1. **`DATABASE_URL`**：必须修改为你本地 MySQL 的实际用户名和密码
2. **`LLM_API_KEY`**：必须填写有效的 DeepSeek API Key，否则智课生成功能无法使用
   - 注册地址：https://platform.deepseek.com/
   - 注册后在"API Keys"页面创建密钥
3. **`DEBUG=true`**：开发阶段务必设为 `true`，否则所有 API 请求都需要携带签名参数

---

## Step 8：初始化数据库

### 8.1 创建数据库

登录 MySQL 并创建数据库：

```bash
mysql -u root -p
```

在 MySQL 命令行中执行：

```sql
CREATE DATABASE IF NOT EXISTS `chaoxing`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

EXIT;
```

### 8.2 执行初始化脚本（推荐）

项目提供了完整的数据库初始化脚本，包含建表语句和示例数据：

```bash
mysql -u root -p --default-character-set=utf8mb4 < scripts/init_db.sql
```

> 该脚本会自动创建 `chaoxing` 数据库和 10 张数据表（users、courses、parse_tasks、scripts、audio_tasks、lessons、qa_sessions、qa_records、learning_progress、adjust_records），并插入示例数据。

### 8.3 验证数据库

```bash
mysql -u root -p -e "USE chaoxing; SHOW TABLES;"
```

应看到类似输出：

```
+--------------------+
| Tables_in_chaoxing |
+--------------------+
| adjust_records     |
| audio_tasks        |
| courses            |
| learning_progress  |
| lessons            |
| parse_tasks        |
| qa_records         |
| qa_sessions        |
| scripts            |
| users              |
+--------------------+
```

---

## Step 9：启动后端服务

### 推荐：Windows 一键启动

项目根目录提供了本地开发脚本：

```cmd
start.bat
```

脚本会检查 `uv`、Node.js 和 npm，自动创建本地 `.env` / `frontend\.env.local`（如不存在），执行 `uv sync`，构建前端，释放旧端口，并启动：

- 后端：`http://127.0.0.1:8001`
- 前端：`http://127.0.0.1:3000`
- Swagger：`http://127.0.0.1:8001/docs`
- 测试面板：`http://127.0.0.1:8001/panel/`

停止服务：

```cmd
stop.bat
```

### 手动启动后端

确保你已经：
- ✅ 激活了 Python 虚拟环境
- ✅ 安装了所有 Python 依赖
- ✅ 配置了 `.env` 文件
- ✅ 初始化了数据库

在**项目根目录**下执行：

```bash
DEBUG=true uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8001
```

**Windows 用户**需要先设置环境变量：

```cmd
# CMD
set DEBUG=true
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8001
```

```powershell
# PowerShell
$env:DEBUG="true"
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8001
```

### 启动成功标志

看到类似以下输出说明后端启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 访问 API 文档

打开浏览器访问：

- **Swagger UI（交互式文档）**：http://localhost:8001/docs
- **ReDoc（阅读式文档）**：http://localhost:8001/redoc
- **健康检查**：http://localhost:8001/health

---

## Step 10：安装并启动前端

> 请**新开一个终端窗口**，保持后端服务运行。

### 10.1 进入前端目录

```bash
cd frontend
```

### 10.2 配置前端环境变量

复制环境变量示例文件（如果没有示例文件，直接创建 `frontend/.env.local`）：

```bash
# macOS / Linux
cat > .env.local <<'EOF'
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
VITE_STATIC_KEY=chaoxing_dev_static_key
VITE_DEFAULT_SCHOOL_ID=sch10001
EOF

# Windows PowerShell
@'
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
VITE_STATIC_KEY=chaoxing_dev_static_key
VITE_DEFAULT_SCHOOL_ID=sch10001
'@ | Set-Content -Encoding utf8 .env.local
```

`.env.local` 文件内容（默认即可，无需修改）：

```env
# 后端服务地址
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
VITE_STATIC_KEY=chaoxing_dev_static_key
VITE_DEFAULT_SCHOOL_ID=sch10001
```

### 10.3 安装前端依赖

```bash
npm install
```

### 10.4 启动前端开发服务器

```bash
npm run dev -- --host 127.0.0.1 --port 3000
```

### 启动成功标志

看到类似以下输出：

```
  VITE v6.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://xxx.xxx.xxx.xxx:3000/
```

打开浏览器访问 http://localhost:3000 即可看到前端页面。

---

## 验证服务是否正常运行

### 1. 后端健康检查

```bash
curl http://localhost:8001/health
```

期望返回：

```json
{"status": "ok", "service": "ChaoXingAgent AI 互动智课服务系统"}
```

### 2. 查看 API 文档

浏览器打开 http://localhost:8001/docs ，应看到完整的 Swagger 交互式 API 文档，包含以下模块：

- 智课生成（课件解析、脚本生成等）
- 实时问答
- 学习进度
- 平台对接
- 系统健康检查

### 3. 前端页面

浏览器打开 http://localhost:3000 ，应看到前端界面。

---

## 常见问题排查（FAQ）

### Q1：`ModuleNotFoundError: No module named 'src'`

**原因**：Python 无法找到 `src` 包。

**解决方案**：

方案 A — 确保从项目根目录运行命令：

```bash
# 必须在 ChaoXingAgent/ 目录下执行
cd /path/to/ChaoXingAgent
uvicorn src.api.app:app --reload
```

方案 B — 将项目根目录加入 Python 路径：

```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
uvicorn src.api.app:app --reload
```

方案 C — 以开发模式安装项目：

```bash
pip install -e .
```

---

### Q2：`Access denied for user 'root'@'localhost'`

**原因**：MySQL 用户名或密码不正确。

**解决方案**：检查 `.env` 文件中的 `DATABASE_URL`，确保用户名和密码与你的 MySQL 配置一致：

```env
DATABASE_URL=mysql+pymysql://root:你的实际密码@127.0.0.1:3306/chaoxing?charset=utf8mb4
```

---

### Q3：`Can't connect to MySQL server on '127.0.0.1'`

**原因**：MySQL 服务未启动。

**解决方案**：

```bash
# macOS
brew services start mysql

# Linux
sudo systemctl start mysql

# Windows — 在"服务"中启动 MySQL 服务，或：
net start mysql
```

---

### Q4：`Unknown database 'chaoxing'`

**原因**：数据库尚未创建。

**解决方案**：执行 [Step 8：初始化数据库](#step-8初始化数据库)。

---

### Q5：前端页面打开后接口报错 / 无法连接后端

**原因**：后端服务未启动，或前端 `.env` 中的后端地址配置错误。

**解决方案**：
1. 确认后端服务正在运行（终端中有 uvicorn 输出）
2. 确认 `frontend/.env.local` 中 `VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1`
3. 确认后端启动时使用了 `--host 0.0.0.0`

---

### Q6：`LLMConfigurationError: Missing API key for provider 'deepseek'`

**原因**：未配置 LLM API Key。

**解决方案**：在项目根目录 `.env` 文件中填写有效的 API Key：

```env
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

> 注意：如果不需要使用智课生成功能（仅测试 API 框架），可以暂时不配置此项，但调用生成相关接口时会报错。

---

### Q7：`pip install` 时报错 `error: Microsoft Visual C++ 14.0 or greater is required`（Windows）

**原因**：部分 Python 包需要 C++ 编译环境。

**解决方案**：安装 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)，勾选"C++ 桌面开发"工作负载。

---

### Q8：端口被占用

**原因**：8001 或 3000 端口已被其他程序使用。

**解决方案**：

```bash
# 查看占用端口的进程
# macOS / Linux
lsof -i :8001

# Windows
netstat -ano | findstr :8001

# 使用其他端口启动
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8002
```

---

## 项目目录结构说明

```
ChaoXingAgent/
├── .env                          # 环境变量配置（需自行创建，不提交到 Git）
├── requirements.txt              # Python 依赖清单
├── setup.py                      # Python 包安装配置
│
├── src/                          # 后端源码
│   ├── main.py                   # CLI 命令行入口
│   ├── api/                      # FastAPI Web 服务
│   │   ├── app.py                # 应用入口（启动文件）
│   │   ├── config.py             # 配置管理（读取 .env）
│   │   ├── deps.py               # 公共依赖
│   │   ├── middleware.py          # 签名验证中间件
│   │   ├── response_models.py    # 响应数据模型
│   │   ├── models/               # 数据库模型
│   │   │   ├── database.py       # 数据库引擎与会话
│   │   │   └── tables.py         # 数据表定义
│   │   ├── routers/              # API 路由
│   │   │   ├── lesson.py         # 智课生成接口
│   │   │   ├── qa.py             # 问答接口
│   │   │   ├── progress.py       # 学习进度接口
│   │   │   └── platform.py       # 平台对接接口
│   │   └── services/             # 业务逻辑层
│   │       ├── lesson_service.py
│   │       ├── qa_service.py
│   │       ├── progress_service.py
│   │       └── platform_service.py
│   ├── agents/                   # AI Agent 层
│   │   ├── QA.py                 # 问答 Agent
│   │   ├── decision.py           # 决策 Agent
│   │   ├── file_parser.py        # 文件解析 Agent
│   │   ├── generate.py           # 生成 Agent
│   │   └── prompts/              # LLM Prompt 模板（YAML）
│   ├── pipelines/                # 业务流水线
│   ├── schemas/                  # 数据结构定义（Pydantic）
│   ├── utils/                    # 工具类
│   │   ├── llm_client.py         # LLM 客户端
│   │   ├── env_utils.py          # 环境变量工具
│   │   ├── extractors/           # 文件内容提取器
│   │   └── renderers/            # PPT 渲染器
│   └── workflows/                # 工作流编排
│
├── frontend/                     # 前端源码（Vue 3 + Vite）
│   ├── .env.local              # 前端本地环境变量（自行创建，不提交）
│   ├── package.json              # 前端依赖清单
│   ├── vite.config.js            # Vite 配置
│   └── src/
│       ├── App.vue               # 根组件
│       ├── main.js               # 入口文件
│       ├── api/                  # API 请求封装
│       └── components/           # 页面组件
│
├── scripts/
│   └── init_db.sql               # 数据库初始化脚本
│
├── tests/                        # 测试代码
├── data/                         # 运行时数据目录
└── docs/                         # 项目文档
```

---

## 快速启动命令速查

```cmd
:: Windows 一键启动（推荐）
start.bat

:: 停止后端和前端
stop.bat
```

```bash
# ===== 一次性环境搭建 =====

# 1. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate.bat       # Windows CMD

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 创建 .env 文件并填写配置（参考 Step 7）

# 4. 初始化数据库
mysql -u root -p --default-character-set=utf8mb4 < scripts/init_db.sql

# 5. 安装前端依赖
cd frontend && npm install && cd ..

# ===== 日常启动 =====

# 启动后端（终端 1）
source venv/bin/activate
DEBUG=true uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8001

# 启动前端（终端 2）
cd frontend && npm run dev -- --host 127.0.0.1 --port 3000
```

---

> 📌 如有其他问题，请查阅 `docs/` 目录下的其他文档，或联系项目维护者。
