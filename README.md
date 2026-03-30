# Smart-SQL - 智能 NL2SQL 查询助手

一款基于自然语言的智能 SQL 查询工具，通过 AI 将自然语言自动转换为 SQL 查询语句，降低数据库使用门槛。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
  - [方式一：Docker Compose 一键部署（推荐）](#方式一docker-compose-一键部署推荐)
  - [方式二：本地开发环境](#方式二本地开发环境)
- [详细配置](#详细配置)
  - [环境变量](#环境变量)
  - [数据源配置](#数据源配置)
  - [AI 模型配置](#ai-模型配置)
- [项目结构](#项目结构)
- [API 接口](#api-接口)
- [常见问题](#常见问题)

---

## 功能特性

- **自然语言转 SQL**：输入自然语言描述，自动生成 SELECT 查询语句
- **多数据库支持**：支持 PostgreSQL、MySQL 等主流数据库
- **SQL 安全扫描**：自动检测高危操作（DELETE/DROP 等），仅允许只读查询
- **查询历史记录**：完整记录所有查询，支持反馈评价
- **术语自定义**：支持业务术语配置，提升 SQL 生成准确性
- **训练样本**：提供问答样例训练，提升模型表现
- **CSV 导出**：支持导出完整查询结果

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy |
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia |
| 数据库 | PostgreSQL 16 + pgvector |
| AI | LangChain + OpenAI/DeepSeek 等 LLM |
| 容器化 | Docker Compose V2 |

---

## 系统要求

- **操作系统**：Windows 10+/macOS 10.14+/Linux (Ubuntu 20.04+)
- **Docker**：Docker Desktop 4.0+ 或 Docker Engine 20.10+
- **内存**：最低 4GB RAM（推荐 8GB+）
- **硬盘**：至少 10GB 可用空间

---

## 快速开始

### 方式一：Docker Compose 一键部署（推荐）

#### 1. 克隆项目

```bash
git clone https://github.com/GMtaozi/Smart-SQL.git
cd Smart-SQL
```

#### 2. 配置环境变量

创建 `.env` 文件：

```bash
# AI API 配置（必需）
OPENAI_API_KEY=sk-your-api-key-here

# JWT 密钥（必需，用于用户认证）
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# 密码加密密钥（必需，用于加密数据源密码）
# 生成方式：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
PASSWORD_ENCRYPTION_KEY=your-fernet-key-here
```

#### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend
```

#### 4. 访问应用

- 前端地址：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

### 方式二：本地开发环境

#### 前置条件

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 + pgvector
- AI API Key（OpenAI/DeepSeek 等）

#### 后端设置

```bash
# 进入后端目录
cd server

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example .env
# 编辑 .env 填入配置

# 初始化数据库
python -c "from server.db.database import init_db; init_db()"

# 启动后端
uvicorn server.main:app --reload --port 8000
```

#### 前端设置

```bash
# 新开终端，进入客户端目录
cd client

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 访问应用

- 前端地址：http://localhost:5173
- 后端地址：http://localhost:8000

---

## 详细配置

### 环境变量

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `OPENAI_API_KEY` | 是 | AI 模型 API Key | `sk-xxxxx` |
| `JWT_SECRET_KEY` | 是 | JWT 签名密钥 | `any-secret-key` |
| `PASSWORD_ENCRYPTION_KEY` | 是 | Fernet 加密密钥 | `xxx` |
| `DATABASE_URL` | 否 | 数据库连接 URL（默认使用 docker-compose 配置） | `postgresql://sqlbot:sqlbot123@localhost:5432/sqlbot` |

**生成 PASSWORD_ENCRYPTION_KEY：**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 数据源配置

1. 登录系统后，进入「数据源管理」
2. 点击「添加数据源」
3. 填写连接信息：
   - **名称**：数据源显示名称
   - **类型**：PostgreSQL 或 MySQL
   - **主机**：数据库服务器地址
   - **端口**：5432（PostgreSQL）或 3306（MySQL）
   - **数据库名**：目标数据库名称
   - **用户名**：数据库用户名
   - **密码**：数据库密码（加密存储）

4. 点击「同步表结构」获取数据库表信息

### AI 模型配置

1. 进入「AI 模型」配置页面
2. 点击「添加模型」
3. 填写配置：
   - **供应商**：OpenAI / DeepSeek / Zhipu / Qianfan
   - **模型名称**：如 `gpt-4o-mini`、`deepseek-chat`
   - **API Key**：供应商提供的 API Key
   - **API 地址**：API endpoint（可选，自定义域名）

---

## 项目结构

```
Smart-SQL/
├── docker-compose.yml     # Docker 编排配置
├── Dockerfile.backend     # 后端 Docker 镜像
├── Dockerfile.frontend     # 前端 Docker 镜像
├── .env.example           # 环境变量模板
├── SPEC.md               # 产品规格说明
├── server/                # 后端源码
│   ├── main.py           # FastAPI 入口
│   ├── api/              # API 路由
│   │   ├── auth.py       # 认证接口
│   │   ├── query.py      # 查询接口
│   │   ├── schema.py     # 数据源管理
│   │   ├── ai_model.py   # AI 模型
│   │   ├── terminology.py # 术语管理
│   │   └── data_training.py # 训练样本
│   ├── services/         # 业务逻辑
│   │   ├── sql_generator.py  # NL→SQL
│   │   ├── sql_guard.py      # SQL 安全
│   │   ├── sql_executor.py   # SQL 执行
│   │   └── vector_store.py   # 向量存储
│   ├── models/          # 数据模型
│   └── db/              # 数据库连接
└── client/             # 前端源码
    ├── src/
    │   ├── views/       # 页面组件
    │   ├── stores/      # 状态管理
    │   ├── api/        # API 调用
    │   └── components/ # 公共组件
    ├── nginx.conf      # Nginx 配置
    └── Dockerfile      # 前端构建
```

---

## API 接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 查询接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/query/generate` | 生成 SQL |
| POST | `/api/query/execute` | 执行 SQL |
| POST | `/api/query/export` | 导出 CSV |
| GET | `/api/query/history` | 查询历史 |

### 数据源接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/schema/datasources` | 添加数据源 |
| GET | `/api/schema/datasources` | 数据源列表 |
| DELETE | `/api/schema/datasources/{id}` | 删除数据源 |
| POST | `/api/schema/tables` | 同步表结构 |
| GET | `/api/schema/tables` | 表列表 |

详细 API 文档请访问：http://localhost:8000/docs

---

## 常见问题

### Q: 启动后提示数据库连接失败？

检查 docker-compose.yml 中的数据库配置是否正确：

```bash
# 进入 postgres 容器检查
docker-compose exec postgres psql -U sqlbot -d sqlbot

# 检查后端日志
docker-compose logs backend | grep -i error
```

### Q: SQL 生成失败？

1. 确认已配置 AI API Key
2. 确认已添加数据源并同步表结构
3. 检查后端日志获取详细错误信息

### Q: 前端页面空白？

```bash
# 重建前端镜像
docker-compose build frontend
docker-compose up -d frontend
```

### Q: 如何查看服务状态？

```bash
# 查看所有服务
docker-compose ps

# 查看资源使用
docker stats

# 查看健康状态
curl http://localhost:8000/health
```

### Q: 如何备份数据库？

```bash
# 创建备份
docker-compose exec postgres pg_dump -U sqlbot sqlbot > backup.sql

# 恢复备份
cat backup.sql | docker-compose exec -T postgres psql -U sqlbot sqlbot
```

---

## 开发指南

### 添加新的 API 接口

1. 在 `server/api/` 目录下创建新的路由文件
2. 定义 Pydantic 模型（输入/输出）
3. 实现业务逻辑
4. 在 `server/main.py` 中注册路由

### 前端组件开发

```bash
cd client
npm run dev    # 开发模式
npm run build  # 生产构建
npm run lint   # 代码检查
```

---

## 许可证

MIT License

---

## 联系方式

- GitHub: https://github.com/GMtaozi/Smart-SQL
- Issues: https://github.com/GMtaozi/Smart-SQL/issues
