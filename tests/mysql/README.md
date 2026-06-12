# MySQL 集成测试套件

直接打到**真实 MySQL**（不是 SQLite）的集成测试，验证：

* 13 张表的 DDL 在 MySQL 9 上能跑通
* 字符集 / 排序规则 / InnoDB 引擎都对
* `LONGTEXT` 字段（`structured_content`、`parser_output` 等）能存大于 64KB 的中文 JSON
* `ON UPDATE CURRENT_TIMESTAMP` 真的会自动 bump `updated_at`
* `UNIQUE` 索引真的会拒绝重复 ID
* utf8mb4 真的能存表情符号 + 中文混合内容
* 路由 → 服务层 → 真 MySQL 的 round-trip 一致

## 安全设计

**永不污染生产数据**：测试用专用数据库 `chaoxing_test`，与生产 `chaoxing` 完全隔离。

每次 session 开始时：
1. `CREATE DATABASE IF NOT EXISTS chaoxing_test ...`
2. `DROP TABLE` 所有现存表（保证 fresh state）
3. `Base.metadata.create_all` 重新建 13 张表
4. 测试在这个临时库里跑
5. session 结束后保留库结构（方便 `mysql -u root -p chaoxing_test` 排查）

## 一键运行

```bash
# 默认（自动 skip）
.venv/bin/python -m pytest tests/mysql/                    # 18 skipped

# opt-in
RUN_MYSQL=1 .venv/bin/python -m pytest tests/mysql/ -v     # 18 passed in ~3s
.venv/bin/python -m pytest tests/mysql/ --run-mysql -v     # 同上

# 单独跑某一组
RUN_MYSQL=1 .venv/bin/python -m pytest tests/mysql/test_schema.py -v
RUN_MYSQL=1 .venv/bin/python -m pytest tests/mysql/test_endpoints_on_mysql.py -v

# 用自定义 MySQL（默认从 .env 的 DATABASE_URL 派生）
MYSQL_TEST_URL="mysql+pymysql://root:pwd@host:3306/test_db?charset=utf8mb4" \
  RUN_MYSQL=1 .venv/bin/python -m pytest tests/mysql/
```

## 测试范围

| 文件 | 测试数 | 关注点 |
|---|---|---|
| `test_schema.py` | 8 | DDL 正确性：表名、引擎、字符集、LONGTEXT 字段、PK 自增、UNIQUE 索引、created_at/updated_at 默认值、CJK + emoji round-trip |
| `test_endpoints_on_mysql.py` | 10 | 业务往返：parse 写入、unique 拒重复、LONGTEXT 200KB round-trip、updated_at 自动更新、parse→script→audio 全链路、KB 创建、知识库 chunk 大文本、progress 持久化、platform syncUser、QASession idempotent |
| **合计** | **18** | — |

## 设计要点

1. **fixture 顺序**：`_bootstrap_mysql_test_db` (autouse) → `app(_bootstrap_mysql_test_db)` → `db(app)`，确保表先 drop 再 create_all，再访问。

2. **强制重建 engine**：API 测试和 e2e 测试可能已在同一 pytest 会话里 import 过 `src.api.app`，缓存了 engine。`app` fixture 显式重建 SQLAlchemy engine 指向 `chaoxing_test`。

3. **MYSQL_TEST_URL 覆盖**：默认从 `.env` 的 `DATABASE_URL` 派生（把 path 替换成 `chaoxing_test`），但允许用 `MYSQL_TEST_URL` 直接指定（CI 多 DB 支持友好）。

4. **失败优雅**：MySQL 不可达时 `pytest.skip` 而非 fail，让"环境问题"和"代码问题"分离。

5. **opt-in**：默认所有测试 skip，需 `--run-mysql` 或 `RUN_MYSQL=1`。

## 何时该新增

* 引入了新表 / 新字段 → 加到 `test_schema.py` 的 `EXPECTED_TABLES` 等常量
* 修改了 LONGTEXT / Index / UNIQUE 约束 → 同上
* 在路由 / 服务层引入了新的"持久化模式"（比如 transaction、批量 upsert）→ 加到 `test_endpoints_on_mysql.py`

不应在这里加：
* 单纯的业务逻辑测试 → `tests/api/`（更快，SQLite）
* 真 LLM / TTS 测试 → `tests/e2e/`

## 故障排查

| 失败信息 | 含义 | 处理 |
|---|---|---|
| `MySQL not reachable: ...` | 服务没起 / 凭据错 | `mysql -u root -p` 验证；检查 `.env` |
| `Unknown database 'chaoxing_test'` | 创建权限不够 | `GRANT CREATE ON *.* TO 'root'@'localhost'` |
| `Specified key was too long; max key length is 3072 bytes` | utf8mb4 + 长 String + 老版本 MySQL | 升到 8.0+ 或缩短 String 长度 |
| `non-utf8mb4 tables: [...]` | 创建库时漏了 charset | `ALTER DATABASE chaoxing_test CHARACTER SET utf8mb4` |
| `updated_at did not advance` | tables.py 的 `_NOW_ON_UPDATE` 失效 | 检查 `tables.py` 的 dialect 判断逻辑 |

## 最后一道防线：审计 production DB 未被污染

每次 mysql 测试跑完，可以用以下命令对生产库做行数审计：

```bash
.venv/bin/python -c "
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='root', password='12345678', database='chaoxing')
cur = conn.cursor()
cur.execute('SHOW TABLES')
for (t,) in cur.fetchall():
    cur.execute(f'SELECT COUNT(*) FROM \`{t}\`')
    print(f'  {t}: {cur.fetchone()[0]} rows')
"
```
