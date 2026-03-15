# SQLModel CRUD

基于 SQLModel 的可复用 CRUD 模块，提供通用的数据库操作基类和代码生成器。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 功能特性

- **通用 CRUD 基类**: 提供同步和异步两种模式的 CRUD 操作基类
- **软删除支持**: 内置软删除和恢复功能
- **数据库连接管理**: 支持 SQLite、PostgreSQL、MySQL 等多种数据库
- **代码生成器**: 根据 SQLModel 模型自动生成 CRUD 代码
- **类型安全**: 完整的类型注解支持
- **异常处理**: 统一的异常处理机制

## 安装

### 使用 uv 安装（推荐）

```bash
uv pip install sqlmodel-crud
```

### 使用 pip 安装

```bash
pip install sqlmodel-crud
```

### 从源码安装

```bash
git clone https://github.com/yourusername/sqlmodel-crud.git
cd sqlmodel-crud
uv pip install -e .
```

## 快速开始

### 1. 定义模型

```python
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    """用户模型"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
```

### 2. 创建 CRUD 类

```python
from sqlmodel_crud import CRUDBase

class UserCRUD(CRUDBase[User, User, User]):
    def __init__(self):
        super().__init__(User)
```

### 3. 使用 CRUD 操作

```python
from sqlmodel_crud import DatabaseManager

# 创建数据库管理器
db = DatabaseManager("sqlite:///app.db")
db.create_tables()

# 使用 CRUD
with db.get_session() as session:
    user_crud = UserCRUD()
    
    # 创建
    user = user_crud.create(session, {"name": "张三", "email": "zhang@example.com"})
    
    # 查询
    user = user_crud.get(session, 1)
    
    # 更新
    user = user_crud.update(session, 1, {"name": "李四"})
    
    # 删除
    user = user_crud.delete(session, 1)
```

## 代码生成器

### 命令行使用

```bash
# 初始化项目
sqlmodel-crud init --models-path app/models --output-dir app/generated

# 生成代码
sqlmodel-crud generate

# 预览模式
sqlmodel-crud generate --dry-run
```

### 编程方式使用

```python
from sqlmodel_crud import ModelScanner, CodeGenerator, GeneratorConfig

# 扫描模型
scanner = ModelScanner()
models = scanner.scan("app/models")

# 配置生成器
config = GeneratorConfig(
    models_path="app/models",
    output_dir="app/generated",
)

# 生成代码
generator = CodeGenerator(config)
files = generator.generate(models)
generator.write_files(files)
```

### 生成后的目录和职责

默认会生成这些文件：

- `config.py`：数据库配置对象 `DatabaseConfig`
- `database.py`：`DatabaseManager`、`db`、`init_database()`、`get_session()` 或 `get_async_session()`
- `__init__.py`：统一导出入口
- `crud/<model>.py`：每个模型一个 CRUD 类
- `models/`：复制后的模型文件（当 `generate_model_copy=true` 时）

典型目录结构：

```text
app/generated/
├── __init__.py
├── config.py
├── database.py
├── crud/
│   ├── user.py
│   └── item.py
└── models/
    ├── __init__.py
    ├── user.py
    └── item.py
```

### 生成代码的推荐用法

同步项目通常这样组织：

```python
# app/db.py
from app.generated import DatabaseConfig, db, init_database


def bootstrap_database() -> None:
    init_database(DatabaseConfig(db_name="app.db", db_dir="data"))
```

```python
# main.py
from app.db import bootstrap_database

bootstrap_database()
```

```python
# app/services/user_service.py
from app.generated import UserCRUD, get_session

user_crud = UserCRUD()


def create_user(data: dict):
    with get_session() as session:
        return user_crud.create(session, data)


def get_user(user_id: int):
    with get_session() as session:
        return user_crud.get(session, user_id)
```

如果一组写操作必须处于同一个事务里，不要在每层都重新开 session，而是由最外层统一开一个 session，再往下传：

```python
from app.generated import UserCRUD, ProfileCRUD, get_session

user_crud = UserCRUD()
profile_crud = ProfileCRUD()


def register_user(user_data: dict, profile_data: dict):
    with get_session() as session:
        user = user_crud.create(session, user_data)
        profile = profile_crud.create(
            session, {**profile_data, "user_id": user.id}
        )
        return user, profile
```

异步项目则使用异步入口：

```python
# app/db.py
from app.generated import DatabaseConfig, init_database


async def bootstrap_database() -> None:
    await init_database(DatabaseConfig(db_name="app.db", db_dir="data"))
```

```python
# app/services/user_service.py
from app.generated import UserCRUD, get_async_session

user_crud = UserCRUD()


async def create_user(data: dict):
    async with get_async_session() as session:
        return await user_crud.create(session, data)
```

### 事务语义

- CRUD 方法会显式接收 `session`
- CRUD 写操作只做 `add/flush/refresh`
- `commit/rollback` 由生成出来的 `get_session()` / `get_async_session()` 统一处理
- 这意味着“一个事务”的边界应该放在 service 层，而不是散落在 CRUD 类内部

### 关闭数据层生成

如果你已经有自己的数据库基础设施，只想生成 CRUD 类，可以关闭数据层文件输出：

```toml
[sqlmodel-crud]
generate_data_layer = false
```

此时只会生成 `crud/` 下的文件，你需要自行提供 session 管理。

## 高级功能

### 异步支持

```python
from sqlmodel_crud import AsyncCRUDBase

class UserCRUD(AsyncCRUDBase[User, User, User]):
    def __init__(self):
        super().__init__(User)

# 异步使用
async with db.get_async_session() as session:
    user_crud = UserCRUD()
    user = await user_crud.create(session, {"name": "张三"})
```

### 软删除

```python
from sqlmodel_crud import CRUDBase, RestoreMixin

class UserCRUD(CRUDBase, RestoreMixin):
    def __init__(self):
        super().__init__(User)

# 软删除
user = user_crud.delete(session, 1, soft=True)

# 恢复
user = user_crud.restore(session, 1)
```

### 批量操作

```python
# 批量创建
users = user_crud.create_multi(session, [
    {"name": "张三", "email": "zhang@example.com"},
    {"name": "李四", "email": "li@example.com"},
])

# 分页查询
users = user_crud.get_multi(
    session,
    skip=0,
    limit=10,
    filters={"is_active": True},
    order_by=[("created_at", "desc")]
)
```

## 项目结构

```
src/sqlmodel_crud/
tests/
README.md
LICENSE
pyproject.toml
```

## 配置

### 配置文件 (.sqlmodel-crud.toml)

```toml
[sqlmodel-crud]
models_path = "app/models"
output_dir = "app/generated"
crud_suffix = "CRUD"
exclude_models = []
generate_data_layer = true
data_layer_db_name = "app.db"
```

**注意**：
- `models_path` 支持目录路径、单文件路径和模块路径
- 输出目录使用固定结构：`crud/`、`models/`
- 当 `models_path` 位于 `output_dir` 内时，模型复制会自动禁用

### 环境变量

```bash
export SQLMODEL_CRUD_MODELS_PATH="app/models"
export SQLMODEL_CRUD_OUTPUT_DIR="app/generated"
```

## 开发

### 安装开发依赖

```bash
uv pip install -e ".[dev]"
```

### 运行测试

```bash
uv run pytest
```

### 代码格式化

```bash
uv run black sqlmodel_crud/ tests/
```

## 许可证

本项目采用 [MIT](LICENSE) 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)
