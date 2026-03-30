# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 项目概述

**智能SQL助手** (原 SQLBot) - 基于自然语言的 NL2SQL 智能查询系统。用户输入自然语言描述，系统自动生成 SQL 查询语句并执行返回结果。

# 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy + LangChain
- **前端**: Vue 3 + TypeScript + Element Plus + Pinia + Vite
- **数据库**: PostgreSQL 16 (业务数据 + pgvector 向量索引)
- **AI**: LLM API (OpenAI/DeepSeek 等 OpenAI 兼容接口)
- **容器化**: Docker Compose V2

# 环境变量 (必须设置)

在 `.env` 文件中配置以下环境变量（参考 `.env.example`）:

```bash
PASSWORD_ENCRYPTION_KEY=<Fernet密钥>     # 数据源密码加密密钥
JWT_SECRET_KEY=<JWT密钥>                 # JWT令牌密钥
OPENAI_API_KEY=<API密钥>                # LLM API密钥
```

**重要**: `PASSWORD_ENCRYPTION_KEY` 必须设置且保持稳定，否则重启后已存储的数据源密码将无法解密。

# 常用命令

```bash
# 启动开发环境
docker-compose up --build

# 强制重建（无缓存）
docker-compose up --build --no-cache

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 进入 PostgreSQL 容器
docker-compose exec postgres psql -U sqlbot -d sqlbot

# 重启后端（代码修改后）
docker-compose restart backend

# 重启前端（代码修改后）
docker-compose restart frontend
```

# 系统架构

## 后端结构 (`server/`)

```
server/
├── main.py              # FastAPI 应用入口
├── api/                 # API 路由层
│   ├── auth.py          # 认证（登录/注册/JWT验证）
│   ├── query.py         # 查询（生成SQL/执行SQL/历史记录）
│   ├── schema.py        # 数据源管理（CRUD/表结构同步）
│   ├── ai_model.py      # AI模型配置
│   ├── terminology.py   # 术语管理
│   └── data_training.py # SQL训练
├── services/            # 业务逻辑层
│   ├── sql_generator.py # NL → SQL（LangChain + LLM）
│   ├── sql_guard.py     # SQL 安全扫描
│   ├── sql_executor.py  # SQL 执行器（只读连接）
│   ├── schema_service.py # 数据源/表结构服务
│   └── vector_store.py  # pgvector RAG 检索
├── models/              # SQLAlchemy ORM 模型
├── db/                  # 数据库连接
└── utils/security.py    # 密码加密/SQL高危词检测
```

## 前端结构 (`client/src/`)

```
client/src/
├── views/              # 页面组件
│   ├── Chat.vue       # 智能问答主界面
│   ├── Datasource.vue # 数据源管理
│   ├── AIModel.vue   # AI模型配置
│   └── ...
├── stores/            # Pinia 状态管理
│   ├── chat.ts       # 对话状态（localStorage持久化）
│   └── auth.ts       # 认证状态
├── api/              # API 调用封装
└── components/       # 公共组件
```

## 核心数据流

```
用户输入自然语言 → Schema RAG检索 → LangChain生成SQL → SQL安全扫描
    → 用户确认 → 执行（只读） → 结果返回 → 记录query_log
```

# 关键约束

## 数据库连接安全

- 数据源密码必须通过 `encrypt_password()`/`decrypt_password()` 加密存储
- SQL执行器使用只读连接，配置 `statement_timeout=30000` 和 `LIMIT 1000`
- `PASSWORD_ENCRYPTION_KEY` 环境变量必须持久化，否则密码无法解密

## API 认证

- 所有 `/api/*` 接口（除 `/api/auth/*` 外）需要 JWT Bearer Token
- Token 验证通过 `server/api/auth.py` 的 `get_current_user_id` 依赖
- 前端将 token 存储在 `localStorage`，通过 axios interceptor 自动附加到请求头

## 密码加密流程

1. 创建/更新数据源时: `encrypt_password(明文密码)` → 存储到 `password_encrypted`
2. 执行SQL查询时: `decrypt_password(密文密码)` → 构建数据库连接
3. 密钥来源: `os.getenv("PASSWORD_ENCRYPTION_KEY")`，未设置则每次启动生成新密钥（导致密码丢失）

# 参考文档

- `ARCHITECTURE.md` - 详细技术架构设计
- `SPEC.md` - 产品规格说明书
- `docker-compose.yml` - 服务编排配置
