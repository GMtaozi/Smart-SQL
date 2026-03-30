# SQLbot 产品规格 (SPEC)

> 版本：v1.0
> 日期：2026-03-28

---

## 1. 产品概述

### 1.1 产品定位

SQLbot 是一款 NL2SQL 智能查询工具，通过自然语言描述自动生成 SQL 查询语句，降低数据库使用门槛。

### 1.2 目标用户

- 业务人员：需要查询数据但不懂 SQL
- 数据分析师：快速获取数据洞察
- 运维人员：日常数据库巡检

---

## 2. 功能需求

### 2.1 核心功能

#### F1: 自然语言转 SQL
- 用户输入自然语言描述
- 系统生成对应的 SELECT 语句
- 支持多表关联查询
- 自动添加 LIMIT 限制

#### F2: SQL 安全扫描
- 词法检测高危关键字（DELETE/DROP 等）
- 语法校验（EXPLAIN）
- JOIN 复杂度限制（最多 3 表）
- 子查询深度限制（最多 2 层）

#### F3: SQL 执行
- 用户确认后执行查询
- 只读模式（statement_timeout=30s）
- 行数限制（最多 1000 行）
- 执行时间统计

#### F4: Schema 管理
- 添加/删除数据源
- 导入表结构元数据
- 表结构自动生成向量
- pgvector 相似度检索

#### F5: 查询历史
- 记录所有查询
- 状态追踪（pending/success/failed）
- 用户反馈评价

#### F6: 用户认证
- 用户注册/登录
- JWT Token 认证
- 密码 bcrypt 加密

### 2.2 用户流程

```
用户登录 → 选择数据源 → 输入自然语言 → 生成SQL → 确认执行 → 查看结果 → 评价反馈
```

---

## 3. 非功能需求

### 3.1 性能

| 指标 | 目标值 |
|------|--------|
| SQL 生成 | < 5s |
| 查询执行 | < 30s（超时限制）|
| 页面响应 | < 200ms |

### 3.2 安全

- 所有接口 JWT 认证
- SQL 只读执行
- 数据库连接加密
- 敏感信息加密存储

### 3.3 可用性

- Docker 一键部署
- 健康检查接口
- 错误提示友好

---

## 4. 数据模型

### 4.1 用户 (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| username | varchar | 用户名（唯一）|
| password_hash | varchar | 密码哈希 |
| email | varchar | 邮箱 |
| created_at | timestamp | 创建时间 |

### 4.2 数据源 (datasources)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| user_id | int | 所属用户 |
| name | varchar | 数据源名称 |
| host | varchar | 主机地址 |
| port | int | 端口 |
| database_name | varchar | 数据库名 |
| username | varchar | 用户名 |
| password_encrypted | varchar | 加密密码 |
| db_type | varchar | 数据库类型 |

### 4.3 表结构 (schema_tables)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| datasource_id | int | 所属数据源 |
| table_name | varchar | 表名 |
| table_comment | text | 表注释 |

### 4.4 列结构 (schema_columns)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| table_id | int | 所属表 |
| column_name | varchar | 列名 |
| data_type | varchar | 数据类型 |
| column_comment | text | 列注释 |
| is_primary_key | int | 是否主键 |

### 4.5 查询日志 (query_logs)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| user_id | int | 用户 |
| datasource_id | int | 数据源 |
| user_query | text | 自然语言 |
| generated_sql | text | 生成SQL |
| status | varchar | 状态 |
| execution_time_ms | float | 执行时间 |
| row_count | int | 返回行数 |

### 4.6 反馈 (query_feedbacks)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| query_log_id | int | 关联查询 |
| rating | int | 评分(1-5) |
| is_correct | int | 是否正确 |
| corrected_sql | text | 纠正SQL |

---

## 5. API 接口

### 5.1 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| GET | /api/auth/me | 当前用户 |

### 5.2 查询

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/query/generate | 生成SQL |
| POST | /api/query/execute | 执行SQL |
| GET | /api/query/history | 查询历史 |
| POST | /api/query/feedback | 提交反馈 |

### 5.3 Schema

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/schema/datasources | 添加数据源 |
| GET | /api/schema/datasources | 数据源列表 |
| DELETE | /api/schema/datasources/{id} | 删除数据源 |
| POST | /api/schema/tables | 添加表结构 |
| GET | /api/schema/tables | 表列表 |
| DELETE | /api/schema/tables/{id} | 删除表结构 |

---

## 6. 页面清单

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录 | /login | 登录/注册 |
| 查询 | / | NL查询主界面 |
| Schema | /schema | Schema管理 |
| 历史 | /history | 查询历史 |

---

## 7. 未来规划

- MCP 协议接入
- Dify/Coze 集成
- 多数据源支持
- SQL 纠错学习
