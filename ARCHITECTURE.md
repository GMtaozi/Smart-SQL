# SQLbot 技术架构设计

> 版本：v1.0
> 作者：大虾（CTO）
> 日期：2026-03-28

---

## 一、技术栈确认

| 层级 | 技术选型 | 理由 |
|------|----------|------|
| **AI 核心** | LLM + RAG（text2vec + pgvector） | 为大模型提供精准的 Schema 上下文，大幅提升 SQL 生成准确率 |
| **后端** | Python + FastAPI + LangChain | 高性能异步 API + LLM 编排框架，Python 生态成熟 |
| **前端** | Vue 3 + Element Plus + @antv/g2 | 成熟组件库 + 数据可视化 |
| **数据库** | PostgreSQL + pgvector | 业务数据 + 向量索引统一存储，架构简洁 |
| **部署** | Docker + MCP | 一键部署，易集成 Dify/Coze |

**技术栈评价：**
- 这套组合是当前做 NL2SQL 的主流方案，pgvector 替代 ES 做向量检索，架构上没问题
- LangChain 可以加速开发，但要注意 v0.3 以后版本差异大，建议锁定版本
- Docker + MCP 的部署设计是加分项，第一版可以先不做 MCP，但目录结构要留好

---

## 二、系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户端 (Browser)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Vue 3 + Element Plus                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ NL 输入   │  │ Schema   │  │ 查询历史  │  │ 结果展示  │   │   │
│  │  │ 界面      │  │ 管理     │  │         │  │ + 可视化  │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST + JWT
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Python)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    LangChain Orchestrator                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │   │
│  │  │ SQL Gen    │  │ SQL Safe   │  │ Vector Retrieve   │   │   │
│  │  │ Chain      │  │ Guard      │  │ (pgvector)        │   │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────┐  ┌─────────┴────────┐  ┌──────────────────┐   │
│  │ Auth Router  │  │ Query Router    │  │ Schema Router    │   │
│  │ (JWT)        │  │ (生成/执行/历史) │  │ (数据源/表/字段)  │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│  PostgreSQL     │  │  LLM API        │  │  业务数据库          │
│  (pgvector)     │  │  (OpenAI/Claude)│  │  (用户配置的目标库)  │
│  业务表+向量索引 │  │                 │  │  (只读连接)         │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
```

**核心数据流：**

```
用户输入 NL → Schema RAG 检索 → LangChain 生成 SQL → SQL 安全扫描 
    → 用户确认 → 执行（只读） → 结果返回 → 记录 query_log
```

---

## 三、文件目录结构

```
sqlbot/
├── docker-compose.yml          # 一键启动（PostgreSQL + Backend + Frontend）
├── Dockerfile.backend
├── Dockerfile.frontend
├── INSTRUCTION.md             # Claude Code 开发指令（本文件）
├── SPEC.md                    # 产品规格（PRD 的技术版）
│
├── server/                    # Python FastAPI 后端
│   ├── main.py               # 应用入口
│   ├── config.py             # 配置管理
│   ├── requirements.txt      # 依赖锁定版本
│   │
│   ├── api/                  # API 路由层
│   │   ├── __init__.py
│   │   ├── auth.py           # 认证接口（登录/注册）
│   │   ├── query.py          # 查询接口（NL→SQL / 执行）
│   │   └── schema.py         # Schema 管理接口
│   │
│   ├── schemas/              # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── query.py
│   │   └── schema.py
│   │
│   ├── services/             # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── sql_generator.py # NL → SQL（LangChain + LLM）
│   │   ├── sql_guard.py      # SQL 安全扫描
│   │   ├── sql_executor.py   # SQL 执行器（只读）
│   │   ├── vector_store.py   # pgvector RAG 检索
│   │   └── auth_service.py   # JWT 认证
│   │
│   ├── models/               # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── datasource.py
│   │   ├── schema_table.py
│   │   ├── schema_column.py
│   │   ├── query_log.py
│   │   └── query_feedback.py
│   │
│   ├── db/                   # 数据库连接
│   │   ├── __init__.py
│   │   ├── database.py      # PostgreSQL 连接
│   │   └── vector.py        # pgvector 初始化
│   │
│   └── utils/                # 工具函数
│       ├── __init__.py
│       └── security.py       # SQL 高危词检测
│
└── client/                   # Vue 3 前端
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── src/
    │   ├── main.ts
    │   ├── App.vue
    │   ├── router/
    │   │   └── index.ts
    │   ├── stores/           # Pinia 状态管理
    │   │   ├── auth.ts
    │   │   └── query.ts
    │   ├── api/              # API 调用封装
    │   │   ├── auth.ts
    │   │   ├── query.ts
    │   │   └── schema.ts
    │   ├── views/            # 页面
    │   │   ├── Login.vue
    │   │   ├── Query.vue     # NL 查询主界面
    │   │   ├── Schema.vue    # Schema 管理
    │   │   └── History.vue   # 查询历史
    │   ├── components/       # 公共组件
    │   │   ├── SqlViewer.vue   # SQL 展示 + 确认执行
    │   │   ├── ResultTable.vue # 结果表格
    │   │   └── SchemaSelector.vue
    │   └── types/            # TypeScript 类型
    │       └── index.ts
    └── Dockerfile
```

---

## 四、模块职责说明

### 4.1 SQL Generator（NL → SQL）

**输入：** 自然语言 + 数据源 ID
**输出：** 生成的 SQL 语句
**流程：**
1. 根据 `datasource_id` 检索相关表的 Schema 信息（表名、字段、描述）
2. 将 Schema 构造成 prompt 上下文
3. 调用 LangChain + LLM 生成 SQL
4. 返回生成的 SQL 和使用的表信息

**Prompt 模板（核心）：**
```
你是一个 SQL 专家。根据以下数据库表结构，将用户的问题翻译成 SQL 语句。

【表结构】
- orders（订单表）:
  - order_id (bigint): 订单ID
  - product_name (varchar): 产品名称
  - sale_amt (decimal): 销售额
  - order_date (date): 下单日期

【用户问题】
{user_query}

【要求】
- 只生成 SELECT 语句，不要 DELETE/DROP/INSERT/UPDATE
- 使用标准 SQL
- 必须指定 LIMIT 限制返回行数（最大1000）

请生成 SQL：
```

### 4.2 SQL Guard（安全扫描）

**输入：** SQL 字符串
**输出：** `{pass: boolean, reason?: string}`

**扫描规则：**
1. 词法检测：是否包含高危关键词（DELETE、DROP、TRUNCATE、ALTER、GRANT、REVOKE、INSERT、UPDATE、CREATE、EXECUTE）
2. 语法校验：通过 `EXPLAIN` 验证语法正确性
3. 复杂度限制：最多 3 表 JOIN，禁止子查询嵌套过深

### 4.3 SQL Executor（执行器）

**输入：** SQL + 数据源连接信息
**输出：** 查询结果（JSON 格式）

**安全约束：**
- 使用数据库只读账号连接（建议为目标库创建一个专用只读用户）
- 设置 `statement_timeout = 30000`（30 秒超时）
- 使用 `LIMIT 1000` 限制结果集大小
- 禁止连接有写入权限的账号

### 4.4 Vector Store（pgvector RAG）

**用途：** 根据用户 Query 检索最相关的 Schema 表结构

**流程：**
1. 表/字段入库时，同时生成向量（text2vec 模型）
2. 查询时，将用户自然语言转为向量
3. 在 pgvector 中做相似度检索，返回 Top-K 相关表结构
4. 将检索结果注入 LLM 的 Prompt 上下文

---

## 五、安全设计总结

| 防线 | 措施 |
|------|------|
| **应用层** | SQL Guard 词法扫描，拦截高危 SQL |
| **数据库层** | 业务数据库只读账号，pgvector 库无写入需求 |
| **LLM 层** | System Prompt 约束输出格式，强调"只生成 SELECT" |
| **执行层** | statement_timeout 30s + LIMIT 1000 |

---

## 六、开发顺序

```
第一阶段：基础设施
  1. 初始化项目（docker-compose、目录结构）
  2. PostgreSQL + pgvector 初始化
  3. 后端：数据库建表（ORM 模型）
  4. 前端：项目骨架（Vue 3 + Vite + Element Plus）

第二阶段：核心功能
  5. 后端：JWT 认证（注册/登录）
  6. 后端：Schema 管理 API（CRUD）
  7. 后端：pgvector 接入（Schema  embedding）
  8. 后端：NL → SQL 生成（LangChain + LLM）
  9. 后端：SQL Guard 安全扫描
  10. 前端：Query 主界面（NL 输入 + SQL 展示 + 确认执行）

第三阶段：辅助功能
  11. 后端：SQL Executor（执行查询）
  12. 后端：Query History API
  13. 前端：History 页面
  14. 前端：Schema 管理页面

第四阶段（可选）：
  15. MCP 协议接入
  16. Dify/Coze 集成
```
