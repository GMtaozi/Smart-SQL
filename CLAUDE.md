# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Smart-SQL - NL2SQL智能查询系统

基于自然语言的SQL查询生成工具，用户输入自然语言描述，系统自动生成SELECT查询语句并执行返回结果。

## 常用命令

```bash
# Docker Compose 开发环境
docker-compose up --build          # 启动所有服务
docker-compose up --build --no-cache  # 强制重建（无缓存）
docker-compose logs -f backend     # 查看后端日志
docker-compose logs -f frontend    # 查看前端日志
docker-compose restart backend     # 重启后端
docker-compose exec postgres psql -U sqlbot -d sqlbot  # 进入数据库

# 本地开发
cd server && uvicorn server.main:app --reload --port 8000  # 后端
cd client && npm run dev                                       # 前端 (Vite)
```

## 环境变量（必需）

```bash
OPENAI_API_KEY=<API密钥>                    # LLM API Key
JWT_SECRET_KEY=<JWT密钥>                     # JWT签名密钥
PASSWORD_ENCRYPTION_KEY=<Fernet密钥>        # 数据源密码加密密钥
# 生成密钥：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**重要**: `PASSWORD_ENCRYPTION_KEY`必须保持稳定，否则重启后已存储的数据源密码将无法解密。

## 架构

### 数据流
```
用户输入自然语言 → Schema检索 → LangChain生成SQL → SQL安全扫描 → 用户确认 → 只读执行 → 返回结果
```

### 后端结构 (server/)
- `main.py` - FastAPI入口，注册路由，初始化数据库
- `api/` - 路由层（auth, query, schema, ai_model, terminology, data_training）
- `services/sql_generator.py` - NL→SQL核心（LangChain + LLM）
- `services/sql_guard.py` - SQL安全扫描（高危词检测、EXPLAIN校验）
- `services/sql_executor.py` - SQL执行器（**只读连接**，statement_timeout=30s）
- `models/` - SQLAlchemy ORM模型
- `db/database.py` - 应用数据库连接（PostgreSQL + pgvector）

### 前端结构 (client/src/)
- `views/Chat.vue` - 智能问答主界面
- `stores/chat.ts` - 对话状态（Pinia，localStorage持久化）
- `stores/auth.ts` - 认证状态
- **注意**: Pinia store使用`storeToRefs`保持响应性，直接解构会丢失响应性

### SQL执行安全
- 所有查询使用**只读连接**
- `sql_executor.py`中`execute()`方法设置`statement_timeout=30000ms`
- 预览模式最多返回10行（`PREVIEW_ROW_LIMIT=10`）
- 高危词（DELETE/DROP/INSERT/UPDATE）由`sql_guard.py`词法检测拦截

### 用户认证
- JWT Bearer Token，存储在`localStorage`
- Token通过axios interceptor自动附加到请求头
- 除`/api/auth/*`外，所有API需要认证

### 前端路由
- `/login` - 公共路由
- `/` - 受保护路由，需JWT
  - `/chat` - 智能问答
  - `/datasource` - 数据源管理
  - `/ai-model` - AI模型配置
  - `/terminology` - 术语管理
  - `/training` - 训练样本
  - `/history` - 查询历史
