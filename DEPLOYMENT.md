# ChaoXingAgent 服务器部署指南

面向**全新 Linux 服务器**的从零部署清单。基线环境 **Ubuntu 22.04 LTS / 24.04 LTS**；其它发行版（CentOS / Rocky / Debian）做了适配说明。

> 全程预计耗时：**30-45 分钟**（含 MySQL 安装 + uv 拉依赖 + Nginx 配置 + HTTPS）。

**关键工具链选择**：
- **依赖管理**：`uv`（不用 `pip` / `venv` / `poetry`）— 极快、可重现、自动管理 Python 版本
- **进程管理**：`systemd`（Linux 原生，无额外依赖）
- **反向代理**：`nginx`（行业标准）
- **数据库**：`MySQL 8.0+`（utf8mb4 是硬要求）

---

## 0. 服务器规格建议

| 资源 | 最低 | 推荐 | 备注 |
|---|---|---|---|
| CPU | 2 核 | 4 核 | LLM 调用主要等网络，本机 CPU 用于 PDF 解析 + PPT 渲染 |
| 内存 | 4 GB | 8 GB | FAISS 索引、edge-tts、LibreOffice 同时跑 |
| 磁盘 | 20 GB | 40 GB | LibreOffice ~1.5G，uv 缓存 ~1G，运行时数据无上限 |
| 网络 | 出站到 LLM API、edge-tts CDN | — | 不通就 e2e 测试会 skip |
| OS | Ubuntu 22.04+ / Debian 12+ / CentOS 9+ | — | uv 会自己装 Python 3.13，发行版无要求 |

---

## 1. 系统包安装

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y \
    git curl ca-certificates \
    libreoffice \
    fonts-noto-cjk fonts-wqy-zenhei fonts-wqy-microhei \
    nginx

# CentOS / Rocky 9
sudo dnf install -y \
    git curl ca-certificates \
    libreoffice \
    google-noto-cjk-fonts wqy-zenhei-fonts \
    nginx
```

**为什么需要这些**：
- **`libreoffice`** — 项目用 `soffice` 把 PPTX 转 PNG 预览（`src/utils/renderers/pptx_renderer.py`）。装完确认 `which soffice` 有返回。
- **CJK 字体** — 渲染 PPT/PNG 时不能让中文变方块。`fc-list :lang=zh | wc -l` 应 ≥1。
- **`nginx`** — 反向代理（详见 §11）。

> ⚠️ **不需要装** `python3.13`、`python3-venv`、`build-essential`、`libssl-dev` 等 Python 编译依赖 — uv 会自己处理。

---

## 2. 安装 uv

uv 是 Astral 出品的 Python 包/虚拟环境管理器，**比 pip 快 10-100 倍**，自带 Python 版本管理。

```bash
# 推荐：官方安装脚本（装到 ~/.local/bin/uv）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或：从 cargo（如有 Rust 工具链）
# cargo install --locked uv

# 让 PATH 生效（普通用户）
source $HOME/.local/bin/env   # 当前 shell
echo 'source $HOME/.local/bin/env' >> ~/.bashrc

# 验证
uv --version    # 期望 0.10.x 以上
```

**uv 工作流核心命令速查**：

| 命令 | 作用 |
|---|---|
| `uv sync` | 按 `pyproject.toml` + `uv.lock` 装依赖（默认含 dev + test） |
| `uv sync --no-dev` | **生产环境**：只装 runtime 依赖（不含 ruff、pytest 等） |
| `uv sync --extra claude` | 加装可选的 `claude_agent_sdk` |
| `uv lock` | 重新生成 `uv.lock`（修改 `pyproject.toml` 后） |
| `uv run <cmd>` | 在 uv 管理的 venv 里跑命令（不需要手动 activate） |
| `uv run python -m uvicorn ...` | 启服务的标准姿势 |
| `uv pip install <pkg>` | 临时装包（不写入 lock） |

uv 会把虚拟环境放在 `<project>/.venv/`，与 `python -m venv` 兼容。

---

## 3. MySQL 8.0+ 安装与配置

```bash
# Ubuntu / Debian
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation  # 设 root 密码、移除 anonymous user

# CentOS / Rocky
sudo dnf install -y mysql-server
sudo systemctl enable --now mysqld
sudo mysql_secure_installation
```

### 创建数据库 + 用户

```bash
sudo mysql -u root -p
```

```sql
-- 创建生产库（utf8mb4 必须，否则中文存不了）
CREATE DATABASE chaoxing
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 创建测试库（给 tests/mysql/ 用，可选）
CREATE DATABASE chaoxing_test
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 业务用户（不要直接用 root）
CREATE USER 'chaoxing'@'localhost' IDENTIFIED BY '<your-strong-password>';
GRANT ALL PRIVILEGES ON chaoxing.* TO 'chaoxing'@'localhost';
GRANT ALL PRIVILEGES ON chaoxing_test.* TO 'chaoxing'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 验证

```bash
mysql -u chaoxing -p chaoxing -e "SHOW VARIABLES LIKE 'character_set_database';"
# 应输出 character_set_database | utf8mb4
```

---

## 4. 拉取项目

```bash
sudo mkdir -p /opt/chaoxing
sudo chown -R "$USER":"$USER" /opt/chaoxing
cd /opt/chaoxing

git clone <你的 git 地址> .
# 或：scp / rsync 上传整个项目目录
```

> ⚠️ **不要上传** `.venv/`、`data/runtime/`、`archive/`、`.codebuddy/`、`__pycache__/`、`*.pyc`。`.gitignore` 已经处理了，但用 `rsync` 时手动确认。
>
> ✅ **必须上传** `pyproject.toml` 和 `uv.lock` — 这两个文件保证服务器装出和本机完全一致的依赖图（hash 校验）。

---

## 5. 用 uv 装依赖

```bash
cd /opt/chaoxing

# 生产部署：只装 runtime 依赖（不要 ruff/pytest 等）
uv sync --no-dev

# 如果要装 Claude Agent SDK（可选）
uv sync --no-dev --extra claude

# 完成后 .venv 已自动生成
ls .venv/bin/python
```

**uv 干了什么**：
1. 读 `.python-version` / `pyproject.toml` 确定要 Python 3.13
2. 如果系统没有 3.13，**自动下载** CPython 3.13.x（Astral 自家镜像）
3. 在 `.venv/` 创建虚拟环境
4. 按 `uv.lock` 装精确版本的依赖（含 hash 校验，防供应链投毒）
5. 整个过程 **30-90 秒**（取决于网络）

### 验证

```bash
# 在 uv 管理的 venv 里跑校验脚本
uv run python -c "
import fastapi, uvicorn, sqlalchemy, pymysql, fitz, pptx, edge_tts, jieba, faiss
print('all critical deps ok')
"
```

> 💡 后续所有命令都建议用 `uv run <cmd>`，不需要手动 `source .venv/bin/activate`。

---

## 6. 配置 `.env`

```bash
cd /opt/chaoxing
cp .env.example .env  # 如有；否则按下方模板创建
chmod 600 .env        # 含密钥，限制权限
```

完整 `.env` 模板：

```ini
# ── 应用 ──────────────────────────────────────────────
DEBUG=false                                # 生产关闭，启用签名校验
STATIC_KEY=<32-byte-random-string>         # 生成: openssl rand -hex 16
SIGNATURE_TIMEOUT_SECONDS=300

# ── 数据库 ────────────────────────────────────────────
DATABASE_URL=mysql+pymysql://chaoxing:<password>@127.0.0.1:3306/chaoxing?charset=utf8mb4
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800

# ── LLM (按你的 provider 填) ──────────────────────────
LLM_PROVIDER=deepseek                       # deepseek / minimax / xfyun / openai
LLM_API_KEY=<your-key>
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_CHAT_COMPLETIONS_PATH=/v1/chat/completions
LLM_TIMEOUT_SECONDS=60
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096
LLM_MAX_CONCURRENT=4
LLM_RETRY_ATTEMPTS=3
LLM_RETRY_DELAY_SECONDS=2

# ── Embedding (RAG 用) ────────────────────────────────
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_BASE_URL=https://api.siliconflow.cn
EMBEDDING_API_KEY=<your-key>
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_ENDPOINT_PATH=/v1/embeddings
EMBEDDING_TIMEOUT_SECONDS=30
EMBEDDING_BATCH_SIZE=32
EMBEDDING_FALLBACK_TO_IN_MEMORY=true

# ── RAG ───────────────────────────────────────────────
RAG_VECTOR_BACKEND=faiss
RAG_INDEX_DIR=/opt/chaoxing/data/rag_indices
RAG_CHUNK_SIZE=400
RAG_CHUNK_OVERLAP=80
RAG_DENSE_TOP_K=10
RAG_FINAL_TOP_K=5
RAG_SCORE_THRESHOLD=0.0
RAG_DENSE_WEIGHT=0.6
RAG_PREFER_SCRIPT_BLOCK_BOOST=0.15
RAG_PREFER_PAGE_BOOST=0.10
RAG_PREFER_SECTION_BOOST=0.05
RAG_TITLE_KEYWORD_BOOST=0.10
RAG_RETRIEVER_CACHE_SIZE=8
RAG_REBUILD_INDEX=false

# ── ASR (语音转文字, 可选) ────────────────────────────
ASR_PROVIDER=openai
ASR_BASE_URL=https://api.siliconflow.cn/v1
ASR_API_KEY=<your-key>
ASR_MODEL=FunAudioLLM/SenseVoiceSmall
ASR_TIMEOUT_SECONDS=30

# ── Agent backend ─────────────────────────────────────
STUDENT_AGENT_BACKEND=claude                # claude / openhands

# ── 路径 (默认即可) ───────────────────────────────────
RUNTIME_DIR=/opt/chaoxing/data/runtime
UPLOAD_DIR=/opt/chaoxing/data/runtime/uploads
AUDIO_DIR=/opt/chaoxing/data/runtime/audio
RENDER_DIR=/opt/chaoxing/data/runtime/renders
LOG_DIR=/opt/chaoxing/data/runtime/logs
WORKSPACE_DIR=/opt/chaoxing/ChaoXingAgentWorkspace
SESSION_DB_PATH=/opt/chaoxing/data/runtime/memory/student_sessions.db
HISTORY_DB_PATH=/opt/chaoxing/data/runtime/memory/student_qa_history.db
```

> ⚠️ **生产环境必须** `DEBUG=false` —— 否则签名校验中间件会被绕过，外部接口完全无认证。

---

## 7. 初始化数据库 + 运行时目录

```bash
cd /opt/chaoxing
uv run python -c "
from src.api.models.database import init_db
from src.utils.paths import paths
paths.ensure()      # 自动创建 runtime/uploads, audio, renders, logs, memory ...
init_db()           # 在 MySQL 上自动建 13 张表
print('init ok')
"
```

期望输出：

```
init ok
```

验证表已建：

```bash
mysql -u chaoxing -p chaoxing -e "SHOW TABLES;"
# 应列出 13 张：adjust_records, audio_tasks, courses, knowledge_base_sources,
# knowledge_bases, knowledge_chunks, learning_progress, lessons, parse_tasks,
# qa_records, qa_sessions, scripts, users
```

---

## 8. 冒烟测试

### 8.1 快速验证

```bash
cd /opt/chaoxing
uv run python -c "from src.api.app import app; print('routes:', len(app.routes))"
# 期望: routes: 38

# 跑 API 契约测试（用 SQLite 隔离，不动 MySQL）
# 注意：契约测试需要 dev/test 依赖，先临时安装一次：
uv sync --extra test
uv run pytest tests/api/ -q -W ignore
# 期望: 78 passed in ~5s
```

### 8.2 真 MySQL 测试

```bash
RUN_MYSQL=1 uv run pytest tests/mysql/ -q -W ignore
# 期望: 18 passed in ~4s
# 用专用 chaoxing_test 库，不动 chaoxing
```

### 8.3 启动 uvicorn 试运行

```bash
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 1
```

另开终端：

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
# 期望: {"status": "ok", "service": "...", "debug": false, "paths": {...}}
```

按 Ctrl+C 停止后清理回 production-only 状态：

```bash
uv sync --no-dev   # 移除 ruff / pytest 等 dev 依赖
```

进入下一步配置 systemd。

---

## 9. 前端构建（可选）

如果你要部署 Vue3 前端，需要先在**任意有 Node 的机器**上构建：

```bash
# 装 Node 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

cd /opt/chaoxing/frontend
npm ci             # 严格按 package-lock.json 装
npm run build      # 产物在 frontend/dist/

ls dist/index.html  # 验证
```

> 测试面板（`frontend/test_panel/index.html`）是单文件 HTML，**不需要构建**，已被 FastAPI 直接挂到 `/panel/`。

---

## 10. systemd 服务化

把 uvicorn 跑成开机自启的系统服务。

### 10.1 创建专用用户（推荐）

```bash
sudo useradd -r -s /bin/false -d /opt/chaoxing chaoxing
sudo chown -R chaoxing:chaoxing /opt/chaoxing
```

### 10.2 让 uv 也能被 chaoxing 用户访问

uv 安装在 `~/.local/bin/uv` 是当前用户的；service user 看不到。两种解决方案：

```bash
# 方案 A：把 uv 放到全局 PATH
sudo cp ~/.local/bin/uv /usr/local/bin/uv
sudo chmod +x /usr/local/bin/uv

# 方案 B：直接在 systemd unit 里用绝对路径
# /home/<your-user>/.local/bin/uv（前提：chaoxing 用户能读）
```

推荐方案 A。

### 10.3 写 systemd unit

```bash
sudo tee /etc/systemd/system/chaoxing.service > /dev/null <<'UNIT'
[Unit]
Description=ChaoXingAgent FastAPI service
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=chaoxing
Group=chaoxing
WorkingDirectory=/opt/chaoxing
EnvironmentFile=/opt/chaoxing/.env

# uv 启动 uvicorn:
#   --workers 数: LLM 调用是 IO 密集，2-4 即可（不像传统 web 服务那样需要 CPU x 2 + 1）
#   --proxy-headers: 让 uvicorn 信任 nginx 转发的 X-Forwarded-* 头
#   --forwarded-allow-ips: 只信任本机 nginx
ExecStart=/usr/local/bin/uv run --no-dev uvicorn src.api.app:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --proxy-headers \
    --forwarded-allow-ips 127.0.0.1 \
    --log-level info

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/chaoxing/data /opt/chaoxing/ChaoXingAgentWorkspace

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now chaoxing
sudo systemctl status chaoxing
```

> **关键改动**：`--host 127.0.0.1` 只监听本机回环 — 外部流量必须经过 Nginx，无法直连 uvicorn。这是 §11 安全模型的基础。

### 10.4 看日志

```bash
sudo journalctl -u chaoxing -f --no-pager
```

---

## 11. Nginx 反向代理（详细）

这一节展开讲清楚：**配置文件去哪、为什么这么写、每条指令的作用**。

### 11.1 Ubuntu/Debian 下 Nginx 的目录结构

`apt install nginx` 后会有这些位置：

```
/etc/nginx/
├── nginx.conf              ← 主配置（改这个的机会很少）
├── conf.d/                  ← 全局补丁（如自定义 log format）
├── sites-available/         ← 你写的所有 server 配置 (源文件)
│   └── default              ← 安装时附送的 demo 配置
├── sites-enabled/           ← 激活的配置 (软链到 sites-available/)
│   └── default → ../sites-available/default
├── snippets/                ← 可复用的配置片段（如 SSL 通用参数）
└── mime.types               ← 文件后缀 → MIME 类型映射

/var/log/nginx/
├── access.log               ← 所有请求的日志
└── error.log                ← Nginx 自身错误 / 上游 5xx

/var/www/                    ← 默认静态文件目录（我们不用）
```

### 11.2 整体的"为什么"

我们要让 Nginx 做四件事：

1. **TLS 终止**（HTTPS）— uvicorn 不擅长 TLS，Nginx 用 OpenSSL 久经考验
2. **反向代理** — 外网 80/443 → 本机 8000
3. **静态文件服务** — `frontend/dist/` 让 Nginx 直接吐，比 FastAPI 快得多
4. **请求保护** — 限制 body 大小、慢客户端、超时阈值

### 11.3 删除默认配置

```bash
sudo rm /etc/nginx/sites-enabled/default
```

> 默认配置占用 80 端口、监听所有路径，会和我们的配置冲突。

### 11.4 创建项目专属配置

```bash
sudo tee /etc/nginx/sites-available/chaoxing > /dev/null <<'NGINX'
# /etc/nginx/sites-available/chaoxing
#
# ChaoXingAgent reverse-proxy + static front-end.
# Two server blocks:
#   1. :80   redirects everything to HTTPS (after Let's Encrypt is set up)
#   2. :443  TLS-terminating proxy to uvicorn @ 127.0.0.1:8000

# ── upstream: 给 uvicorn 起个别名，方便 keepalive 和后续多 worker ──
upstream chaoxing_backend {
    server 127.0.0.1:8000 fail_timeout=10s max_fails=3;
    keepalive 32;          # nginx ↔ uvicorn 之间复用连接（HTTP/1.1 keepalive）
}

# ── HTTP → HTTPS 强制跳转 ────────────────────────────
server {
    listen      80;
    listen      [::]:80;
    server_name your-domain.com;     # ← 改成你的域名

    # Let's Encrypt 验证用，certbot 会临时往这里写 challenge 文件
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }

    # 其它一切跳 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# ── HTTPS 主服务 ─────────────────────────────────────
server {
    listen      443 ssl;
    listen      [::]:443 ssl;
    http2 on;
    server_name your-domain.com;     # ← 改成你的域名

    # ── TLS 证书（certbot 自动填这两行）──
    # 装完 certbot 后这两行会被替换成正确路径
    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # ── 安全相关 headers ──
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options    nosniff;
    add_header X-Frame-Options           SAMEORIGIN;
    add_header Referrer-Policy           "no-referrer-when-downgrade";

    # ── 上传体积限制 ──
    # 课件上传可能 50-100M（PPT/PDF），所以放宽
    client_max_body_size 200M;
    client_body_buffer_size 1M;
    # 慢客户端 (slowloris) 防御
    client_body_timeout 60s;
    client_header_timeout 30s;

    # ── 日志 ──
    access_log /var/log/nginx/chaoxing_access.log;
    error_log  /var/log/nginx/chaoxing_error.log warn;

    # ───────────────────────────────────────────────
    # 1) 静态前端 — 由 nginx 直接吐，绕过 FastAPI
    # ───────────────────────────────────────────────
    location /web/ {
        alias /opt/chaoxing/frontend/dist/;
        # 单页应用：找不到资源时回落到 index.html，让 Vue Router 处理路由
        try_files $uri $uri/ /web/index.html;

        # 强缓存带 hash 的资源
        location ~* \.(js|css|png|jpg|jpeg|gif|svg|woff2?)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }

    # ───────────────────────────────────────────────
    # 2) 测试面板 — 让 nginx 直接挂，省一个 FastAPI 调用
    #    （也可以让 FastAPI 处理；二选一即可）
    # ───────────────────────────────────────────────
    location /panel/ {
        alias /opt/chaoxing/frontend/test_panel/;
        try_files $uri $uri/ /panel/index.html;
    }

    # ───────────────────────────────────────────────
    # 3) API + 其它一切 → 反代到 uvicorn
    # ───────────────────────────────────────────────
    location / {
        proxy_pass http://chaoxing_backend;

        # ── HTTP 协议 & keepalive ──
        proxy_http_version 1.1;
        proxy_set_header   Connection "";       # 保持空，启用 upstream keepalive

        # ── 转发原始客户端信息 ──
        # uvicorn 看到的 client.host 默认是 nginx 的 IP（127.0.0.1）
        # 加上 X-Real-IP / X-Forwarded-* 后业务侧可拿到真实 IP
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   X-Forwarded-Host  $host;
        proxy_set_header   X-Forwarded-Port  $server_port;

        # ── 超时 ──
        # parse / generate 这种长任务可能跑 1-3 分钟（即使 BackgroundTasks
        # 在异步执行，FastAPI 的 endpoint 也可能在等 LLM 响应）
        proxy_connect_timeout 30s;
        proxy_send_timeout    300s;
        proxy_read_timeout    300s;

        # ── 上游缓冲 ──
        # 关闭缓冲让 SSE / 流式响应可工作（学生 QA 未来可能流式输出）
        proxy_buffering    off;
        proxy_request_buffering off;
    }
}
NGINX
```

### 11.5 把配置激活

Nginx 只读 `sites-enabled/` 里的文件 — 用软链激活：

```bash
sudo ln -sf /etc/nginx/sites-available/chaoxing /etc/nginx/sites-enabled/

# 校验配置语法
sudo nginx -t
# 期望: nginx: configuration file /etc/nginx/nginx.conf test is successful

# 重新加载（不中断现有连接）
sudo systemctl reload nginx
```

> **`reload` vs `restart`**：`reload` 只让主进程重读配置、新 worker 接收新连接、老 worker 处理完手头请求再退出；`restart` 会断开所有连接。生产环境改配置永远用 `reload`。

### 11.6 让 Nginx 用户能读到项目目录

`frontend/dist/` 的所有者是 `chaoxing`，但 Nginx 跑在 `www-data`（Ubuntu）/ `nginx`（CentOS）用户下，它**也需要读权限**：

```bash
# 让 nginx 加入 chaoxing group
sudo usermod -a -G chaoxing www-data       # Ubuntu
sudo usermod -a -G chaoxing nginx          # CentOS

# 让 group 也能读
sudo chmod -R g+rX /opt/chaoxing/frontend
```

或者更简洁地放开父目录的 X 位（exec 位允许 cd 进入）：

```bash
sudo chmod o+x /opt/chaoxing
sudo chmod -R o+rX /opt/chaoxing/frontend
```

### 11.7 配置 HTTPS（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx

# 先准备 challenge 目录（上面 nginx 配置里引用的）
sudo mkdir -p /var/www/letsencrypt
sudo chown -R www-data:www-data /var/www/letsencrypt

# 让 certbot 自动改 nginx 配置 + 申请证书 + 重载 nginx
sudo certbot --nginx -d your-domain.com

# certbot 会询问邮箱（接收过期通知）+ 是否同意条款
# 完成后 nginx 配置里的 ssl_certificate 路径会被自动填好

# 自动续期（certbot 装好后已经设了 systemd timer）
sudo systemctl list-timers | grep certbot   # 验证
```

如果你**没有域名只有 IP**，可以跳过 HTTPS，把上面的 :443 server block 改成 :80：

```nginx
server {
    listen 80 default_server;
    server_name _;
    # ... 把整个 :443 block 的内容搬过来，删掉 ssl_* 行
}
```

但生产**强烈建议**有域名 + HTTPS，否则签名校验是明文走的。

### 11.8 验证整条链路

```bash
# 1. nginx 在监听 80/443
sudo ss -tlnp | grep nginx
# 期望两行：80 和 443

# 2. uvicorn 只在 127.0.0.1:8000，外网访问不到
sudo ss -tlnp | grep 8000
# 期望: 127.0.0.1:8000  （不是 0.0.0.0:8000）

# 3. 通过 nginx 拿到 health
curl -sI https://your-domain.com/health
# HTTP/2 200

# 4. 通过 nginx 走全链路
curl -s https://your-domain.com/api/v1/lesson/list | python3 -m json.tool
```

### 11.9 看日志

```bash
# Nginx 访问日志（每个请求一行）
sudo tail -f /var/log/nginx/chaoxing_access.log

# Nginx 错误日志（502/504、上游不通等）
sudo tail -f /var/log/nginx/chaoxing_error.log

# uvicorn 日志（应用层异常）
sudo journalctl -u chaoxing -f --no-pager
```

### 11.10 Nginx 故障 7 大常见现象

| 现象 | Nginx 错误日志关键字 | 排查 |
|---|---|---|
| **502 Bad Gateway** | `connect() failed` | uvicorn 没起：`systemctl status chaoxing` |
| **504 Gateway Timeout** | `upstream timed out` | LLM 太慢，调高 `proxy_read_timeout` |
| **413 Request Entity Too Large** | `client intended to send too large body` | 调大 `client_max_body_size` |
| **403 Forbidden（静态资源）** | `Permission denied` | nginx 用户读不到 dist/，见 §11.6 |
| **301 死循环** | `too many redirects` | 多个 server block 都 `return 301`，检查 sites-enabled/ |
| **HTTPS 证书警告** | — | certbot 没跑成功；看 `/var/log/letsencrypt/letsencrypt.log` |
| **WebSocket 断开**（未来扩展） | `client closed prematurely` | 缺 `proxy_set_header Upgrade $http_upgrade` |

---

## 12. 防火墙

```bash
# UFW (Ubuntu)
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # 包含 80 + 443
sudo ufw enable
sudo ufw status verbose

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http --add-service=https --add-service=ssh
sudo firewall-cmd --reload
```

> **不要**对外暴露 8000 — uvicorn 已经只监听 127.0.0.1，加上防火墙只放行 22/80/443，是双重保险。

---

## 13. 日常运维

### 看日志

```bash
sudo journalctl -u chaoxing -f --no-pager           # 应用日志
tail -f /opt/chaoxing/data/runtime/logs/*.log        # 业务结构化日志
sudo tail -f /var/log/nginx/chaoxing_access.log      # Nginx 访问
sudo tail -f /var/log/nginx/chaoxing_error.log       # Nginx 错误
```

### 重启服务

```bash
sudo systemctl restart chaoxing      # 重启应用
sudo systemctl reload nginx          # 重载 Nginx 配置（不断连）
```

### 部署新版本

```bash
cd /opt/chaoxing
sudo systemctl stop chaoxing

git pull                              # 或 scp 上传新代码

# 同步依赖（uv 自动检测 lock 变化）
uv sync --no-dev

# DB schema 变更（项目用 SQLAlchemy create_all，幂等）
uv run python -c "from src.api.models.database import init_db; init_db()"

sudo systemctl start chaoxing
sudo journalctl -u chaoxing -n 20 --no-pager   # 看启动是否正常
```

### 备份数据库

```bash
sudo crontab -e
# 加一行：每天凌晨 3 点全量备份
0 3 * * * mysqldump -u chaoxing -p<password> chaoxing | gzip > /var/backups/chaoxing_$(date +\%Y\%m\%d).sql.gz
# 保留最近 30 天
0 4 * * * find /var/backups -name 'chaoxing_*.sql.gz' -mtime +30 -delete
```

### 备份运行时产物

```bash
0 4 * * 1 tar czf /var/backups/chaoxing_runtime_$(date +\%Y\%m\%d).tar.gz \
    /opt/chaoxing/data/runtime/uploads \
    /opt/chaoxing/data/runtime/renders \
    /opt/chaoxing/data/runtime/audio
```

---

## 14. 故障排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `uv: command not found` | PATH 没设 | `source ~/.local/bin/env` 或 `cp ~/.local/bin/uv /usr/local/bin/` |
| `uv sync` 卡住 | 镜像慢 | `UV_HTTP_TIMEOUT=120 uv sync` 或换镜像 `UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple` |
| `routes: 38` 失败 | 依赖没装全 | `uv sync` 重跑，看错误 |
| `Lost connection to MySQL` | DB_POOL_RECYCLE 太大 | 改成 1800 (= 30min) |
| `pymysql.err.ProgrammingError: 1146` | 没跑 init_db | `uv run python -c "from src.api.models.database import init_db; init_db()"` |
| `LibreOffice not found, falling back` | 没装 libreoffice | `apt install libreoffice && which soffice` |
| PPT 渲染中文方块 | 没装 CJK 字体 | `apt install fonts-noto-cjk && fc-cache -fv` |
| edge-tts 503 / timeout | GFW 阻断微软 CDN | 用代理（`https_proxy=...`）或 skip 音频功能 |
| LLM 401 | API_KEY 错 | `curl -H "Authorization: Bearer $LLM_API_KEY" $LLM_BASE_URL/v1/models` |
| 中文乱码 | DB charset 不是 utf8mb4 | `ALTER DATABASE chaoxing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` |
| 502 Bad Gateway | uvicorn 没起 | `systemctl status chaoxing` |
| 504 Gateway Timeout | proxy_read_timeout 不够 | nginx 配置改大到 600s |
| 413 Request Entity | client_max_body_size 不够 | 改大到 200M |
| 进程 OOM 被杀 | LLM 并发 + FAISS 同时占内存 | 调小 `LLM_MAX_CONCURRENT`，加 swap |

---

## 15. 部署完成检查清单

- [ ] `uv --version` 输出 0.10+
- [ ] `mysql -u chaoxing -p chaoxing -e "SHOW TABLES"` 返回 13 张表
- [ ] `which soffice` 有返回（LibreOffice 已装）
- [ ] `fc-list :lang=zh | wc -l` ≥ 1（CJK 字体已装）
- [ ] `cat /opt/chaoxing/.env | grep DEBUG` 是 `DEBUG=false`
- [ ] `cat /opt/chaoxing/.env | grep STATIC_KEY` **不是默认值**
- [ ] `chmod 600 /opt/chaoxing/.env`
- [ ] `sudo systemctl is-active chaoxing` 输出 `active`
- [ ] `sudo systemctl is-active nginx` 输出 `active`
- [ ] `sudo ss -tlnp | grep 8000` 显示 `127.0.0.1:8000`（**不是** `0.0.0.0:8000`）
- [ ] `curl -s http://127.0.0.1:8000/health | jq .status` 返回 `"ok"`
- [ ] `curl -s https://your-domain.com/health` 通过 Nginx 也能访问
- [ ] `journalctl -u chaoxing -n 50` 没有 ERROR / Traceback
- [ ] `nginx -t` 配置语法 OK
- [ ] `ufw status` 显示 80/443 allow，8000 没暴露
- [ ] DB 备份 cron 已设
- [ ] HTTPS 证书有效（`curl -vI https://your-domain.com 2>&1 | grep HTTP`）

全部 ✓ 就部署完成。

---

## 附录 A：最小化部署（演示用）

```bash
# 1. 装系统包
sudo apt install -y libreoffice fonts-noto-cjk mysql-server git

# 2. 装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env

# 3. 拉项目 + 装依赖（uv 会自动装 Python 3.13）
git clone <repo> /opt/chaoxing && cd /opt/chaoxing
uv sync --no-dev

# 4. 配 .env（最小集合）
cat > .env <<'EOF'
DEBUG=true
DATABASE_URL=mysql+pymysql://root:<pwd>@127.0.0.1:3306/chaoxing?charset=utf8mb4
LLM_API_KEY=<key>
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
EOF

# 5. 建库 + 跑
mysql -u root -p -e "CREATE DATABASE chaoxing CHARACTER SET utf8mb4"
uv run python -c "from src.api.models.database import init_db; init_db()"
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# 浏览器打开 http://<server-ip>:8000/panel/
```

---

## 附录 B：依赖资源体积参考

| 项目 | 体积 |
|---|---|
| uv 自身 | ~30 MB |
| uv 缓存（首次 sync 后） | ~600 MB |
| Python 3.13 (uv 管理) | ~50 MB |
| `.venv` (装完 sync --no-dev) | ~700 MB |
| LibreOffice | ~1.5 GB |
| MySQL 8 (含 chaoxing 库) | ~500 MB |
| Noto CJK 字体 | ~150 MB |
| 项目代码（不含 .venv / uv 缓存） | ~50 MB |
| frontend/dist 构建产物 | ~5 MB |
| 总计 | **~3 GB** |
| 运行 1 天后的 data/runtime/ 增长 | ~100 MB / 节课 |

---

## 附录 C：本地开发也用 uv（可选）

如果你的本机还在用 `python -m venv` + `pip`，强烈建议也切到 uv：

```bash
# 装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 在项目根目录
cd /Users/.../ChaoXingAgent
rm -rf .venv                  # 删掉旧的
uv sync                        # 含 dev/test 依赖

# 一切 Python 命令前面加 `uv run`
uv run pytest tests/api/
uv run uvicorn src.api.app:app --reload
uv run ruff check src/
```

uv 的优势：
- 装包速度比 pip 快 10-100 倍（重度并行 + Rust 实现）
- 自动管 Python 版本（不用手动装 3.13）
- `uv.lock` 跨平台精确锁定（hash 校验）
- 与 `requirements.txt` / `pyproject.toml` / `pip` 全兼容

---

## 附录 D：Nginx 配置文件常见疑惑

**Q: 为啥配置放 `sites-available/` 而不是 `conf.d/`？**

A: Debian/Ubuntu 系传统：`sites-available/` 是"备选库"，`sites-enabled/` 是"激活集"。要禁用某个站点只需 `rm /etc/nginx/sites-enabled/xxx`，源文件依然在；CentOS 系一般直接用 `conf.d/` 平铺，没有这个区分。我们这里跟 Ubuntu 习惯。

**Q: `sites-available` 里的文件会被 nginx 读到吗？**

A: **不会**。nginx 只 `include /etc/nginx/sites-enabled/*`。`sites-available/` 只是个"草稿目录"。

**Q: 为啥 `proxy_pass` 用 upstream 而不是直接 `proxy_pass http://127.0.0.1:8000`？**

A: 三个好处：
1. 后续要加 `keepalive 32` — 这只能在 upstream block 里写
2. 加多个后端做负载均衡时只改 upstream 一处
3. 加 `fail_timeout` / `max_fails` 让 nginx 自动暂时摘除挂掉的实例

**Q: `proxy_set_header Connection ""` 干嘛的？**

A: HTTP/1.1 默认 `Connection: keep-alive`，但 nginx 转发到上游时**默认改成 `close`**（怪行为）。把 Connection header 显式置空，nginx 才会去使用 upstream 的 keepalive 池，省一次 TCP 三次握手。

**Q: 为啥 `proxy_buffering off`？**

A: 默认开启会让 nginx 先把上游的响应**完整缓存到磁盘**才返给客户端。对 SSE / 流式 LLM 响应是灾难（学生 QA 未来可能流式输出）。关掉就是 fall-through。代价：上游变快了，nginx 不会"吸收"慢客户端，但项目流量量级用不着。

**Q: `try_files $uri $uri/ /web/index.html` 是什么？**

A: SPA（单页应用）必杀技。Vue Router 的 `/lesson/123` 这种路径在服务器上其实没有对应文件，浏览器刷新会 404。`try_files` 让 nginx：
1. 找 `$uri`（具体文件，如 `/web/assets/foo.js`）
2. 找 `$uri/`（目录，自动找 index.html）
3. 都没有就回落到 `/web/index.html`，让 Vue 自己处理路由

**Q: HTTPS 配置里那些 `include /etc/letsencrypt/options-ssl-nginx.conf`？**

A: certbot 会自动生成这个文件，里面是 Mozilla 推荐的 TLS 配置（禁用老协议、开启 OCSP stapling、cipher 顺序等）。不用自己写。

---

## 附录 E：相关文档

- 测试套件：`tests/api/README.md`、`tests/mysql/README.md`、`tests/e2e/README.md`
- 接口规范：`docs/api_design.md`
- 项目契约：`Dev_docs/PROJECT_BRIEF.md`、`Dev_docs/CONTRACT.md`
- 学生侧后端：`docs/student_backend_integration.md`
