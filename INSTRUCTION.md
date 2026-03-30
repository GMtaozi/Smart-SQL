# SQLbot 开发指令

## 项目概述

SQLbot 是一个基于自然语言到 SQL (NL2SQL) 的智能查询系统，使用 LLM + RAG (pgvector) 技术栈。

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 核心 | LLM (GPT-4o-mini) + pgvector RAG |
| 后端 | Python + FastAPI + LangChain |
| 前端 | Vue 3 + Element Plus + G2 |
| 数据库 | PostgreSQL + pgvector |
| 部署 | Docker + Docker Compose |

## 快速开始

### 1. 环境准备

- Docker Desktop
- Node.js 20+
- Python 3.11+
- OpenAI API Key

### 2. 启动服务

```bash
# 复制环境变量文件
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 3. 本地开发

**后端：**
```bash
cd server
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

**前端：**
```bash
cd client
npm install
npm run dev
```

## 目录结构

```
sqlbot/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── server/
│   ├── main.py           # FastAPI 入口
│   ├── config.py         # 配置管理
│   ├── requirements.txt
│   ├── api/              # API 路由
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑
│   ├── models/           # SQLAlchemy ORM
│   ├── db/               # 数据库连接
│   └── utils/            # 工具函数
└── client/
    ├── src/
    │   ├── api/          # API 调用
    │   ├── stores/       # Pinia 状态
    │   ├── views/        # 页面组件
    │   └── components/   # 公共组件
    └── ...
```

## 开发规范

### API 规范

- RESTful 风格
- JWT Bearer Token 认证
- 统一错误响应格式
- 请求/响应使用 Pydantic 模型

### 数据库规范

- 使用 SQLAlchemy ORM
- 表名使用蛇形命名
- 索引规范：
  - 主键自动索引
  - 外键字段加索引
  - 频繁查询字段加索引

### 安全规范

- SQL Guard 词法扫描
- 数据库只读账号
- JWT Token 认证
- CORS 配置

## 测试

```bash
# 后端测试
cd server
pytest

# 前端测试
cd client
npm run test
```

## 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps
```
