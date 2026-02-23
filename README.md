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
uv pip install sqlmodel-curd
```

### 使用 pip 安装

```bash
pip install sqlmodel-curd
```

### 从源码安装

```bash
git clone https://github.com/yourusername/sqlmodel-curd.git
cd sqlmodel-curd
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
models = scanner.scan_module("app.models")

# 配置生成器
config = GeneratorConfig(
    models_path="app/models",
    output_dir="app/generated",
    generators=["crud"],
)

# 生成代码
generator = CodeGenerator(config)
files = generator.generate(models)
generator.write_files(files)
```

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
sqlmodel_curd/
├── sqlmodel_crud/          # 核心模块
│   ├── base.py             # CRUD 基类
│   ├── database.py         # 数据库管理
│   ├── exceptions.py       # 异常类
│   ├── types.py            # 类型定义
│   ├── scanner.py          # 模型扫描器
│   ├── generator.py        # 代码生成器
│   ├── detector.py         # 变更检测
│   ├── config.py           # 配置管理
│   ├── cli.py              # 命令行接口
│   └── templates/          # 代码模板
├── tests/                  # 测试模块
├── examples/               # 示例代码
├── README.md               # 项目文档
├── LICENSE                 # 许可证
└── pyproject.toml          # 项目配置
```

## 配置

### 配置文件 (.sqlmodel-crud.toml)

```toml
[sqlmodel-crud]
models_path = "app/models"
output_dir = "app/generated"
generators = ["crud"]
crud_suffix = "CRUD"
exclude_models = []
generate_data_layer = true
data_layer_db_name = "app.db"
data_layer_db_dir = "AppData"
```

### 环境变量

```bash
export SQLMODEL_CRUD_MODELS_PATH="app/models"
export SQLMODEL_CRUD_OUTPUT_DIR="app/generated"
export SQLMODEL_CRUD_GENERATORS="crud,schemas"
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
