# SQLAlchemy存储

<cite>
**本文引用的文件**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)
- [src/agentscope/memory/_working_memory/_base.py](file://src/agentscope/memory/_working_memory/_base.py)
- [src/agentscope/message/_message_base.py](file://src/agentscope/message/_message_base.py)
- [docs/tutorial/en/src/task_memory.py](file://docs/tutorial/en/src/task_memory.py)
- [docs/tutorial/zh_CN/src/task_memory.py](file://docs/tutorial/zh_CN/src/task_memory.py)
- [tests/memory_test.py](file://tests/memory_test.py)
- [pyproject.toml](file://pyproject.toml)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖分析](#依赖分析)
7. [性能考虑](#性能考虑)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本文件面向AgentScope的SQLAlchemy异步存储实现，系统性梳理AsyncSQLAlchemyMemory类的ORM存储架构与运行机制，覆盖数据库连接管理、异步操作支持、事务处理、ORM映射与表结构、索引优化、连接池配置、批量写入、并发控制、错误处理与回滚策略，并给出针对MySQL、PostgreSQL、SQLite、Oracle的配置思路与最佳实践建议。同时提供查询优化、批量操作、连接复用、迁移与版本管理、性能监控与备份恢复的实施方案要点。

## 项目结构
- 核心实现位于工作记忆模块的SQLAlchemy适配层，采用异步SQLAlchemy ORM进行消息持久化与标记管理。
- 教程与测试文件提供了连接字符串示例、连接池配置范式与并发写入验证。
- 依赖声明中包含SQLAlchemy与异步驱动（如aiosqlite），满足跨数据库的统一抽象。

```mermaid
graph TB
subgraph "工作记忆"
A["_sqlalchemy_memory.py<br/>AsyncSQLAlchemyMemory"]
B["_base.py<br/>MemoryBase 抽象基类"]
end
subgraph "消息模型"
C["_message_base.py<br/>Msg 消息类"]
end
subgraph "教程与示例"
D["task_memory.py<br/>SQLite 示例与连接池范式"]
E["task_memory.py(zh_CN)<br/>中文示例"]
end
subgraph "测试"
F["memory_test.py<br/>并发写入与多租户测试"]
end
subgraph "依赖"
G["pyproject.toml<br/>SQLAlchemy与异步驱动依赖"]
end
A --> B
A --> C
D --> A
E --> A
F --> A
G --> A
```

**图表来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)
- [src/agentscope/memory/_working_memory/_base.py](file://src/agentscope/memory/_working_memory/_base.py)
- [src/agentscope/message/_message_base.py](file://src/agentscope/message/_message_base.py)
- [docs/tutorial/en/src/task_memory.py](file://docs/tutorial/en/src/task_memory.py)
- [docs/tutorial/zh_CN/src/task_memory.py](file://docs/tutorial/zh_CN/src/task_memory.py)
- [tests/memory_test.py](file://tests/memory_test.py)
- [pyproject.toml](file://pyproject.toml)

**章节来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)
- [pyproject.toml](file://pyproject.toml)

## 核心组件
- AsyncSQLAlchemyMemory：基于异步SQLAlchemy ORM的持久化存储，支持用户与会话隔离、消息标记、顺序索引、批量插入与并发安全。
- MemoryBase：内存存储抽象基类，定义统一的add/delete/get_memory/update_messages_mark等接口契约。
- Msg：消息载体，提供to_dict/from_dict序列化能力，被存储为JSON列。

关键特性
- 异步会话管理：支持传入AsyncEngine或外部AsyncSession；内部维护会话工厂与复用策略。
- 并发安全：写入路径使用互斥锁，保证并发add不会产生主键冲突与索引重复。
- 事务语义：写入会话封装自动提交/回滚，异常时回滚并上抛。
- 批量写入：消息标记批量插入，减少外键约束检查次数。
- 查询优化：按session_id过滤，结合索引列维持消息顺序，支持按标记过滤与排除过滤。

**章节来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)
- [src/agentscope/memory/_working_memory/_base.py](file://src/agentscope/memory/_working_memory/_base.py)
- [src/agentscope/message/_message_base.py](file://src/agentscope/message/_message_base.py)

## 架构总览
AsyncSQLAlchemyMemory通过异步SQLAlchemy ORM构建三层模型：用户-会话-消息，消息可附加多个标记。初始化时自动创建表与用户/会话记录，后续所有读写均限定在当前user_id与session_id范围内。

```mermaid
classDiagram
class MemoryBase {
+add(...)
+delete(...)
+get_memory(...)
+update_messages_mark(...)
+size()
+clear()
}
class AsyncSQLAlchemyMemory {
-_db_session
-_session_factory
-_lock
-_initialized
+session
+__aenter__()
+__aexit__()
+close()
+_create_table()
+_write_session()
+_get_next_index()
+_make_message_id()
+add(...)
+get_memory(...)
+size()
+clear()
+delete(...)
+delete_by_mark(...)
+update_messages_mark(...)
}
class MessageTable {
+id
+msg
+session_id
+index
+session
+marks
}
class MessageMarkTable {
+msg_id
+mark
}
class SessionTable {
+id
+user_id
+user
+messages
}
class UserTable {
+id
+sessions
}
class Msg {
+to_dict()
+from_dict()
}
MemoryBase <|-- AsyncSQLAlchemyMemory
AsyncSQLAlchemyMemory --> MessageTable : "使用"
AsyncSQLAlchemyMemory --> SessionTable : "使用"
AsyncSQLAlchemyMemory --> UserTable : "使用"
MessageTable --> SessionTable : "外键"
SessionTable --> UserTable : "外键"
MessageTable --> MessageMarkTable : "一对多"
AsyncSQLAlchemyMemory --> Msg : "序列化/反序列化"
```

**图表来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)
- [src/agentscope/message/_message_base.py](file://src/agentscope/message/_message_base.py)

## 详细组件分析

### AsyncSQLAlchemyMemory类
- 初始化与会话管理
  - 接受AsyncEngine或AsyncSession；若传入Engine则创建async_sessionmaker，内部持有会话实例并在失效时重建。
  - 会话绑定引擎，确保连接生命周期与事务边界可控。
- 并发与事务
  - 写入路径通过asyncio.Lock串行化，避免并发写入导致的主键冲突与索引重复。
  - 使用异步上下文管理器封装写入会话，异常时自动回滚，成功时提交。
- 表结构与索引
  - MessageTable：主键复合键（user_id-session_id-msg_id），JSON列存储消息体，BigInteger索引列维护顺序。
  - MessageMarkTable：消息与标记的多对多桥接，主键(msg_id, mark)，支持去重。
  - SessionTable与UserTable：用户-会话层级，外键关联消息表。
- 查询与过滤
  - 默认按session_id过滤，优先命中索引；支持按mark精确过滤与排除过滤；最终按index升序返回。
- 批量写入
  - 消息写入前先查重，跳过已存在主键；标记写入使用bulk_insert_mappings，减少外键约束检查成本。
- 生命周期管理
  - 支持上下文管理协议与显式close，确保会话释放与状态复位。

```mermaid
sequenceDiagram
participant Caller as "调用方"
participant Mem as "AsyncSQLAlchemyMemory"
participant Sess as "AsyncSession"
participant Conn as "数据库"
Caller->>Mem : add(memories, marks, skip_duplicated)
Mem->>Mem : _create_table()
Mem->>Sess : begin/flush
Mem->>Conn : INSERT INTO message(...)
Mem->>Sess : flush()
Mem->>Conn : INSERT INTO message_mark(...) (bulk)
Conn-->>Sess : OK
Sess-->>Mem : commit 或 rollback
Mem-->>Caller : 完成
```

**图表来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

**章节来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

### ORM映射与表结构
- 用户(UserTable)：id为主键，与会话一对多。
- 会话(SessionTable)：id为主键，外键指向users.id，与消息一对多。
- 消息(MessageTable)：id为复合主键(user_id-session_id-msg_id)，msg为JSON列，session_id为外键，index为排序索引。
- 标记(MessageMarkTable)：msg_id与mark组成联合主键，实现消息到标记的多对多。

```mermaid
erDiagram
USERS {
string id PK
}
SESSION {
string id PK
string user_id FK
}
MESSAGE {
string id PK
json msg
string session_id FK
bigint index
}
MESSAGE_MARK {
string msg_id PK
string mark PK
}
USERS ||--o{ SESSION : "拥有"
SESSION ||--o{ MESSAGE : "包含"
MESSAGE ||--o{ MESSAGE_MARK : "被标记"
```

**图表来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

**章节来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

### 查询流程与优化
- get_memory查询路径
  - 步骤1：按session_id过滤，利用索引快速缩小范围。
  - 步骤2：可选按mark内连接过滤，仅在需要时执行。
  - 步骤3：可选按exclude_mark子查询排除，避免全表扫描。
  - 步骤4：按index升序返回，保证消息顺序。
- 索引策略
  - session_id在MessageTable上具备索引，确保按会话查询高效。
  - 复合主键与外键约束保障数据一致性与级联删除行为。
- 批量操作
  - flush后批量插入标记，减少往返与约束检查次数。
  - 删除时先删标记再删消息，确保跨引擎一致性。

```mermaid
flowchart TD
Start(["进入 get_memory"]) --> CheckMark["是否提供 mark?"]
CheckMark --> |是| JoinMark["内连接标记表并过滤"]
CheckMark --> |否| OrderIndex["直接按 index 升序"]
JoinMark --> ExcludeCheck["是否提供 exclude_mark?"]
ExcludeCheck --> |是| Subquery["子查询排除指定标记的消息ID"]
ExcludeCheck --> |否| Fetch["执行查询"]
Subquery --> Fetch
Fetch --> OrderIndex
OrderIndex --> End(["返回结果"])
```

**图表来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

**章节来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

### 并发与事务处理
- 并发写入
  - 通过asyncio.Lock串行化add写入，避免重复主键与索引冲突。
  - 测试覆盖并发add场景，验证索引唯一性与连续性。
- 事务语义
  - 写入会话上下文管理器在异常时自动回滚，成功时提交，确保一致性。
- 会话复用
  - 内部会话在失效时重建，避免跨请求共享无效会话句柄。

**章节来源**
- [tests/memory_test.py](file://tests/memory_test.py)
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)

## 依赖分析
- SQLAlchemy与异步驱动
  - 项目依赖SQLAlchemy核心库与异步驱动（如aiosqlite），满足SQLite、PostgreSQL、MySQL等数据库的统一抽象。
- 连接池与会话工厂
  - 教程示例展示如何通过create_async_engine与async_sessionmaker配置连接池参数（如pool_size、max_overflow、pool_timeout），并在FastAPI中注入会话依赖。
- 依赖来源
  - SQLAlchemy核心库与异步驱动在pyproject.toml中声明，确保跨数据库兼容性。

```mermaid
graph LR
A["pyproject.toml"] --> B["SQLAlchemy 核心"]
A --> C["异步驱动(如 aiosqlite)"]
D["task_memory.py"] --> E["create_async_engine"]
D --> F["async_sessionmaker"]
E --> B
F --> B
```

**图表来源**
- [pyproject.toml](file://pyproject.toml)
- [docs/tutorial/en/src/task_memory.py](file://docs/tutorial/en/src/task_memory.py)
- [docs/tutorial/zh_CN/src/task_memory.py](file://docs/tutorial/zh_CN/src/task_memory.py)

**章节来源**
- [pyproject.toml](file://pyproject.toml)
- [docs/tutorial/en/src/task_memory.py](file://docs/tutorial/en/src/task_memory.py)
- [docs/tutorial/zh_CN/src/task_memory.py](file://docs/tutorial/zh_CN/src/task_memory.py)

## 性能考虑
- 异步I/O与连接池
  - 使用异步引擎与会话工厂，配合连接池参数提升高并发场景吞吐。
- 批量写入
  - flush后批量插入标记，减少约束检查与往返次数。
- 索引与查询
  - session_id索引与按索引排序，降低查询成本。
- 并发控制
  - 写入路径加锁，避免重复主键与索引冲突，保障数据一致性。
- 连接复用
  - 内部会话在失效时重建，避免跨请求共享无效会话。

[本节为通用性能指导，不直接分析具体文件]

## 故障排查指南
- 主键冲突与重复消息
  - add时可通过skip_duplicated跳过已存在主键；并发场景下加锁避免重复。
- 删除一致性
  - 删除消息时先删标记再删消息，确保跨引擎一致性与外键约束。
- 事务回滚
  - 写入会话异常时自动回滚，需检查异常堆栈定位问题。
- 会话状态
  - close后会重置初始化标志，避免脏状态影响后续操作。
- 并发写入验证
  - 测试覆盖并发add场景，验证索引唯一性与连续性，定位竞态条件。

**章节来源**
- [src/agentscope/memory/_working_memory/_sqlalchemy_memory.py](file://src/agentscope/memory/_working_memory/_sqlalchemy_memory.py)
- [tests/memory_test.py](file://tests/memory_test.py)

## 结论
AsyncSQLAlchemyMemory通过异步SQLAlchemy ORM实现了高性能、可扩展、强一致的工作记忆存储。其核心优势在于：用户-会话隔离、消息标记体系、索引优化、批量写入、并发安全与事务回滚。结合连接池与上下文管理，可在生产环境（如FastAPI）中稳定运行。对于数据库迁移、版本管理、性能监控与备份恢复，建议结合SQLAlchemy生态工具链与项目部署实践制定方案。

[本节为总结性内容，不直接分析具体文件]

## 附录

### 数据库配置示例与最佳实践
- SQLite（内存/文件）
  - 连接字符串示例：sqlite+aiosqlite:///./test_memory.db 或 sqlite+aiosqlite:///:memory:
  - 连接池参数：pool_size、max_overflow、pool_timeout等
- PostgreSQL
  - 连接字符串示例：postgresql+asyncpg://user:password@host:port/dbname
  - 连接池参数：同上
- MySQL
  - 连接字符串示例：mysql+aiomysql://user:password@host:port/dbname
  - 连接池参数：同上
- Oracle
  - 连接字符串示例：oracle+oracledb//user:password@host:port/service_name
  - 连接池参数：同上

[本节为通用配置指导，不直接分析具体文件]

### 连接池与会话注入（FastAPI示例要点）
- 使用create_async_engine创建带连接池的异步引擎。
- 使用async_sessionmaker创建会话工厂，配置expire_on_commit=False等参数。
- 通过Depends注入AsyncSession，确保每个请求独立会话，异常时回滚，结束后关闭。

**章节来源**
- [docs/tutorial/en/src/task_memory.py](file://docs/tutorial/en/src/task_memory.py)
- [docs/tutorial/zh_CN/src/task_memory.py](file://docs/tutorial/zh_CN/src/task_memory.py)

### 数据库迁移、版本管理、性能监控与备份恢复
- 迁移与版本管理
  - 建议结合SQLAlchemy Alembic进行迁移管理，遵循版本化变更策略。
- 性能监控
  - 结合OpenTelemetry等观测体系，采集数据库延迟、连接池利用率、慢查询等指标。
- 备份与恢复
  - 针对SQLite可直接复制文件；对PostgreSQL/MySQL/Oracle采用官方备份工具定期备份，制定恢复演练计划。

[本节为通用实施方案，不直接分析具体文件]