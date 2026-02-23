# 🗄️ SQLModel CRUD 基础设施模块

## 📋 项目概述

**SQLModel CRUD** 是一个基于 SQLModel 的可复用 CRUD 基础设施代码库，专为 PyQt 中小型应用设计。该模块提供了一套完整的数据库操作抽象层，使开发者能够快速构建稳定、可维护的数据访问层，无需重复编写基础的增删改查代码。

### 🎯 适用场景

- 🖥️ **PyQt 桌面应用**：为中小型 PyQt 应用提供统一的数据访问层
- 🚀 **快速原型开发**：快速搭建数据库操作功能，加速项目迭代
- ♻️ **多项目复用**：标准化的 CRUD 模式，可在不同项目间复用
- 👥 **团队协作**：统一的编码规范，降低团队成员的学习成本

### ✨ 核心优势

| 特性 | 说明 |
|------|------|
| 📦 **开箱即用** | 继承基类即可获得完整 CRUD 功能 |
| 🔒 **类型安全** | 基于泛型的完整类型提示，IDE 智能补全友好 |
| ⚡ **同步/异步双支持** | 同时支持同步和异步数据库操作 |
| 🛡️ **软删除支持** | 内置软删除功能，保护数据安全 |
| 🤖 **代码生成器** | 根据模型自动生成 CRUD 代码、Schema |
| ⚠️ **异常体系** | 统一的异常处理机制，错误信息清晰 |
| 🔧 **灵活扩展** | 易于自定义查询方法和业务逻辑 |

---

## 🛠️ 技术栈说明

### 📚 核心依赖

| 依赖库 | 版本要求 | 用途 |
|--------|----------|------|
| 🐍 Python | >= 3.11 | 运行环境 |
| 🗃️ SQLModel | >= 0.0.35 | ORM 核心，结合 SQLAlchemy 和 Pydantic |
| 🔌 SQLAlchemy | >= 2.0.0 | 数据库引擎和 ORM 功能 |
| ✅ Pydantic | >= 2.0.0 | 数据验证和序列化 |
| 📝 Jinja2 | >= 3.1.6 | 代码生成模板引擎 |
| ⌨️ Typer | >= 0.12.0 | CLI 命令行接口 |
| 🎨 Rich | >= 13.0.0 | 终端输出美化 |

### 🔄 异步支持

- **aiosqlite** >= 0.22.1：SQLite 异步驱动
- 支持 PostgreSQL (asyncpg) 和 MySQL (aiomysql) 异步驱动

---

## 🏗️ MVP 架构设计

本项目采用 **MVP（Model-View-Presenter）架构**设计，专门为 PyQt 中小型应用优化。

### 架构原则

1. **模型与数据访问分离**：SQLModel 模型仅定义数据结构，CRUD 类负责数据访问
2. **会话通过方法传入**：CRUD 类构造函数接收模型类型，数据库会话通过方法参数传入
3. **强制基类继承**：生成的 CRUD 类强制继承 `CRUDBase`/`AsyncCRUDBase`，获得完整功能
4. **专注于 PyQt 场景**：不生成 Web API 代码，专注桌面应用需求

### 生成的代码结构

```python
# app/crud/user.py
from sqlmodel_crud import CRUDBase
from app.models.user import User

class UserCRUD(CRUDBase[User, User, User]):
    """User 模型的 CRUD 操作类。"""

    def __init__(self):
        """初始化 CRUD 操作类。"""
        super().__init__(User)

    # 自动拥有完整 CRUD 能力，无需手动实现
```

### 使用方式

```python
# 会话通过方法参数传入，支持会话复用
db = DatabaseManager("sqlite:///app.db")
user_crud = UserCRUD()

with db.get_session() as session:
    # 会话作为参数传入
    user = user_crud.create(session, {"name": "张三"})
    found = user_crud.get(session, user.id)
```

---

## 📥 安装与配置

### 1. 环境要求

确保系统已安装 Python 3.11 或更高版本：

```bash
python --version
```

### 2. 安装依赖

使用 `uv` 工具安装依赖（推荐）：

```bash
# 安装 uv（如未安装）
pip install uv

# 安装项目依赖
uv sync
```

或使用 pip：

```bash
pip install sqlmodel>=0.0.35 sqlalchemy>=2.0.0 pydantic>=2.0.0
```

### 3. 验证安装

```bash
# 查看 CLI 帮助
uv run sqlmodel-crud --help

# 或
python -m sqlmodel_crud.cli --help
```

---

## 🧩 核心功能模块说明

### 📁 模块结构

```
sqlmodel_crud/
├── 📄 __init__.py      # 模块入口，导出主要类
├── 📄 base.py          # CRUD 基类（CRUDBase, AsyncCRUDBase）
├── 📄 database.py      # 数据库连接管理器
├── 📄 exceptions.py    # 异常类和错误码
├── 📄 types.py         # 类型定义
├── 📄 scanner.py       # 模型扫描器
├── 📄 generator.py     # 代码生成器
├── 📄 detector.py      # 变更检测器
├── 📄 config.py        # 配置管理
├── 📄 cli.py           # 命令行接口
└── 📁 templates/       # 代码生成模板
    ├── 📝 crud.py.j2
    └── 📝 schemas.py.j2
```

### 1. CRUD 基类 (base.py)

#### 🔄 CRUDBase - 同步 CRUD 基类

提供通用的同步数据库操作方法：

| 方法 | 功能 | 返回值 |
|------|------|--------|
| 🔍 `get(session, id)` | 根据 ID 获取单条记录 | `ModelType \| None` |
| 🔎 `get_or_raise(session, id)` | 获取记录，不存在抛出异常 | `ModelType` |
| 📃 `get_multi(session, ...)` | 获取多条记录（支持分页、过滤、排序） | `List[ModelType]` |
| ➕ `create(session, obj_in)` | 创建新记录 | `ModelType` |
| ➕➕ `create_multi(session, objs_in)` | 批量创建记录 | `List[ModelType]` |
| ✏️ `update(session, id, obj_in)` | 更新记录 | `ModelType` |
| 🗑️ `delete(session, id, soft=False)` | 删除记录（支持软删除） | `ModelType` |
| 🔢 `count(session, filters)` | 统计记录数 | `int` |
| ✅ `exists(session, id)` | 检查记录是否存在 | `bool` |

#### ⚡ AsyncCRUDBase - 异步 CRUD 基类

与 `CRUDBase` 方法签名相同，所有方法为异步实现（使用 `async/await`）。

#### 🔀 Mixin 类

- **SoftDeleteMixin**：软删除功能支持
- **RestoreMixin**：同步恢复软删除记录
- **AsyncRestoreMixin**：异步恢复软删除记录

### 2. 数据库管理器 (database.py)

`DatabaseManager` 提供统一的数据库连接管理：

```python
from sqlmodel_crud import DatabaseManager

# 创建数据库管理器
db = DatabaseManager(
    database_url="sqlite:///app.db",
    echo=False,              # 是否打印 SQL
    pool_size=5,             # 连接池大小
    max_overflow=10,         # 最大溢出连接
)

# 创建表
db.create_tables()

# 使用上下文管理器获取会话
with db.get_session() as session:
    # 执行数据库操作
    pass

# 异步模式
async with db.get_async_session() as session:
    # 执行异步数据库操作
    pass
```

**支持的数据库 URL 格式：**

| 数据库 | 同步 URL | 异步 URL |
|--------|----------|----------|
| 🪶 SQLite | `sqlite:///path.db` | `sqlite+aiosqlite:///path.db` |
| 🐘 PostgreSQL | `postgresql://user:pass@host/db` | `postgresql+asyncpg://user:pass@host/db` |
| 🐬 MySQL | `mysql+pymysql://user:pass@host/db` | `mysql+aiomysql://user:pass@host/db` |

### 3. 异常体系 (exceptions.py)

统一的异常处理机制：

```python
from sqlmodel_crud import (
    CRUDError,
    ValidationError,
    NotFoundError,
    DatabaseError,
    DuplicateError,
)

try:
    user = user_crud.get_or_raise(session, 999)
except NotFoundError as e:
    print(f"❌ 记录不存在: {e}")
except DuplicateError as e:
    print(f"⚠️ 数据重复: {e}")
except DatabaseError as e:
    print(f"💥 数据库错误: {e}")
```

### 4. 代码生成器

#### 🔍 模型扫描器 (scanner.py)

```python
from sqlmodel_crud import ModelScanner

scanner = ModelScanner()
models = scanner.scan_module("app.models")  # 扫描模块
# 或
models = scanner.scan_module("app/models.py")  # 扫描文件
```

#### 🤖 代码生成器 (generator.py)

```python
from sqlmodel_crud import CodeGenerator, GeneratorConfig

config = GeneratorConfig(
    output_dir="app/generated",
    generators=["crud", "schemas"],
)

generator = CodeGenerator(config)
files = generator.generate(models)
generator.write_files(files)
```

#### 📊 变更检测器 (detector.py)

```python
from sqlmodel_crud import ChangeDetector

detector = ChangeDetector(".sqlmodel-crud-snapshot.json")
changes = detector.detect_changes(models)

if changes:
    print(detector.get_summary(changes))
    detector.save_snapshot(models)
```

---

## 💡 使用示例

### 示例 1：基础 CRUD 操作

```python
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

from sqlmodel_crud import CRUDBase, DatabaseManager


# 定义实体模型
class User(SQLModel, table=True):
    """👤 用户模型"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    age: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


# 定义 CRUD 类
class UserCRUD(CRUDBase[User, User, User]):
    def __init__(self):
        super().__init__(User)

    def get_by_email(self, session, email: str) -> Optional[User]:
        """📧 根据邮箱查找用户"""
        from sqlmodel import select
        statement = select(User).where(User.email == email)
        return session.execute(statement).scalars().first()


# 使用示例
def main():
    # 初始化数据库
    db = DatabaseManager("sqlite:///example.db")
    db.create_tables()

    user_crud = UserCRUD()

    # ➕ 创建记录
    with db.get_session() as session:
        user = user_crud.create(session, {
            "name": "张三",
            "email": "zhangsan@example.com",
            "age": 25
        })
        print(f"✅ 创建用户: ID={user.id}, 姓名={user.name}")

    # 🔍 查询记录
    with db.get_session() as session:
        user = user_crud.get(session, 1)
        print(f"🔍 查询用户: {user.name if user else '未找到'}")

    # ✏️ 更新记录
    with db.get_session() as session:
        updated = user_crud.update(session, 1, {"name": "张三丰", "age": 26})
        print(f"✏️ 更新用户: 姓名={updated.name}, 年龄={updated.age}")

    # 🗑️ 删除记录
    with db.get_session() as session:
        deleted = user_crud.delete(session, 1)
        print(f"🗑️ 删除用户: {deleted.name}")

    db.close()


if __name__ == "__main__":
    main()
```

### 示例 2：软删除功能

```python
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

from sqlmodel_crud import CRUDBase, RestoreMixin, DatabaseManager


class Article(SQLModel, table=True):
    """📄 文章模型（支持软删除）"""
    __tablename__ = "articles"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)


class ArticleCRUD(CRUDBase, RestoreMixin):
    """📄 文章 CRUD 类（支持软删除恢复）"""

    def __init__(self):
        super().__init__(Article)


# 使用示例
def main():
    db = DatabaseManager("sqlite:///example.db")
    db.create_tables()

    article_crud = ArticleCRUD()

    with db.get_session() as session:
        # ➕ 创建文章
        article = article_crud.create(session, {
            "title": "示例文章",
            "content": "这是文章内容"
        })
        print(f"✅ 创建文章: ID={article.id}")

        # 🗑️ 软删除
        deleted = article_crud.delete(session, article.id, soft=True)
        print(f"🗑️ 软删除文章: {deleted.is_deleted}")

        # ❌ 此时 get 方法不会返回已软删除的记录
        not_found = article_crud.get(session, article.id)
        print(f"❌ 查询已删除文章: {not_found}")  # None

        # ♻️ 恢复软删除
        restored = article_crud.restore(session, article.id)
        print(f"♻️ 恢复文章: {restored.is_deleted}")

    db.close()


if __name__ == "__main__":
    main()
```

### 示例 3：异步操作

```python
import asyncio
from typing import Optional
from sqlmodel import SQLModel, Field

from sqlmodel_crud import AsyncCRUDBase, AsyncRestoreMixin, DatabaseManager


class Product(SQLModel, table=True):
    """📦 产品模型"""
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    price: float
    is_deleted: bool = Field(default=False)


class ProductCRUD(AsyncCRUDBase, AsyncRestoreMixin):
    def __init__(self):
        super().__init__(Product)


async def main():
    # 使用异步数据库 URL
    db = DatabaseManager("sqlite+aiosqlite:///async_example.db")
    await db.create_tables_async()

    product_crud = ProductCRUD()

    async with db.get_async_session() as session:
        # ➕ 异步创建
        product = await product_crud.create(session, {
            "name": "笔记本电脑",
            "price": 5999.00
        })
        print(f"✅ 创建产品: ID={product.id}")

        # 🔍 异步查询
        found = await product_crud.get(session, product.id)
        print(f"🔍 查询产品: {found.name}")

        # ✏️ 异步更新
        updated = await product_crud.update(session, product.id, {"price": 5499.00})
        print(f"✏️ 更新价格: {updated.price}")

        # 🗑️ 异步删除
        deleted = await product_crud.delete(session, product.id)
        print(f"🗑️ 删除产品: {deleted.name}")

    await db.close_async()


if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 4：使用 CLI 生成代码（开箱即用）

代码生成器现在支持生成完整的数据层基础设施，让你真正实现开箱即用：

#### 步骤 1：准备模型文件

首先创建一个模型文件，例如 `TestData/models/user.py`：

```python
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

from sqlmodel_crud import CRUDBase, DatabaseManager


# 定义实体模型
class User(SQLModel, table=True):
    """👤 用户模型"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    age: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
```

#### 步骤 2：编写生成脚本

创建 `test_generate.py` 脚本：

```python
"""测试代码生成"""
from sqlmodel_crud import generate

# 测试生成 - 使用正确的路径配置
# 注意：models_path 应该指向原始模型路径，output_dir 是生成代码的输出目录
# 两者不应该重叠，否则会导致循环导入问题
files = generate(
    models_path="TestData/models",  # 原始模型路径（数据源）
    output_dir="data",              # 生成代码的输出目录（与 models_path 不同）
    use_async=False,
    generators=["crud"],            # 只生成 CRUD，不生成 Schema（PyQt 桌面应用不需要）
    exclude_models=["BaseModel"]
)

print(f"生成了 {len(files)} 个文件:")
for f in files:
    print(f"  - {f.file_path} ({f.generator_type})")
```

运行生成脚本：

```bash
uv run python test_generate.py
```

#### 步骤 3：查看生成的文件结构

生成的文件结构（PyQt 桌面应用简化版）：

```
data/
├── __init__.py          # 统一导出所有接口（db, User, UserCRUD）
├── config.py            # 数据库配置
├── database.py          # 数据库初始化（包含 db 单例）
├── crud/                # CRUD 类目录
│   └── user.py          # UserCRUD 类
└── models/              # 模型目录（从源路径复制）
    └── user.py          # User 模型
```

#### 步骤 4：编写测试代码

创建 `test_curd.py` 测试生成的代码：

```python
from data import db, UserCRUD, User

# 初始化数据库（自动创建表，应用启动时调用一次）
db.init_database()

# 使用 CRUD 操作数据
user_crud = UserCRUD()

with db.get_session() as session:
    # 创建用户 - 直接使用字典传入数据
    user = user_crud.create(session, {"name": "张三", "email": "zhangsan@example.com"})
    print(f"✅ 创建用户: ID={user.id}")

    # 查询用户
    found = user_crud.get(session, user.id)
    print(f"🔍 查询用户: {found.name}")

    # 更新用户 - 使用字典进行部分更新
    updated = user_crud.update(session, user.id, {"name": "张三丰"})
    print(f"✏️ 更新用户: {updated.name}")

    # 删除用户
    deleted = user_crud.delete(session, user.id)
    print(f"🗑️ 删除用户: {deleted.name}")
```

运行测试：

```bash
uv run python test_curd.py
```

预期输出：

```
✅ 创建用户: ID=1
🔍 查询用户: 张三
✏️ 更新用户: 张三丰
🗑️ 删除用户: 张三丰
```

#### 其他 CLI 命令

```bash
# 初始化项目配置
uv run sqlmodel-crud init --models-path app/data/models --output-dir app/data

# 预览模式（不实际写入文件）
uv run sqlmodel-crud generate --dry-run

# 强制重新生成
uv run sqlmodel-crud generate --force
```

⚠️ **重要提示**：确保 `output_dir` 与 `models_path` 不重叠。例如：
- ✅ 正确：`models_path = "TestData/models"`, `output_dir = "data"`
- ✅ 正确：`models_path = "models"`, `output_dir = "app/data"`
- ❌ 错误：`models_path = "app/data/models"`, `output_dir = "app/data"`（会导致路径重叠）

### 示例 5：开箱即用 - 使用生成的数据层

```python
# 使用生成的数据层，无需手动配置数据库
from data import db, UserCRUD, User

# 初始化数据库（自动创建表，应用启动时调用一次）
db.init_database()

# 使用 CRUD 操作数据
user_crud = UserCRUD()

with db.get_session() as session:
    # 创建用户 - 直接使用字典传入数据
    user = user_crud.create(session, {"name": "张三", "email": "zhangsan@example.com"})
    print(f"✅ 创建用户: ID={user.id}")

    # 查询用户
    found = user_crud.get(session, user.id)
    print(f"🔍 查询用户: {found.name}")

    # 更新用户 - 使用字典进行部分更新
    updated = user_crud.update(session, user.id, {"name": "张三丰"})
    print(f"✏️ 更新用户: {updated.name}")

    # 删除用户
    deleted = user_crud.delete(session, user.id)
    print(f"🗑️ 删除用户: {deleted.name}")
```

**优势**：
- `db` 是单例模式，整个应用共享同一个数据库连接
- 无需手动管理 `DatabaseManager` 实例
- 自动使用配置中的数据库路径
- 直接使用原始模型类，无需额外的 Schema 层（适合 PyQt 桌面应用）

### 示例 6：分页和过滤

```python
from sqlmodel_crud import CRUDBase, DatabaseManager

# 假设已定义 User 模型和 UserCRUD 类
db = DatabaseManager("sqlite:///example.db")
user_crud = UserCRUD()

with db.get_session() as session:
    # 📄 基础分页
    users = user_crud.get_multi(session, skip=0, limit=10)

    # 🔍 带过滤的分页
    active_users = user_crud.get_multi(
        session,
        skip=0,
        limit=20,
        filters={"is_active": True}
    )

    # 📊 带排序的分页
    sorted_users = user_crud.get_multi(
        session,
        skip=0,
        limit=10,
        order_by=[("created_at", "desc"), ("name", "asc")]
    )

    # 🔢 统计
    total = user_crud.count(session)
    active_count = user_crud.count(session, filters={"is_active": True})

    print(f"👥 总用户数: {total}, 激活用户数: {active_count}")
```

---

## 🔧 自定义扩展指南

### 1. 添加自定义查询方法

```python
from sqlmodel import select, func
from sqlmodel_crud import CRUDBase


class OrderCRUD(CRUDBase[Order, Order, Order]):
    def __init__(self):
        super().__init__(Order)

    def get_by_user_id(self, session, user_id: int):
        """👤 获取指定用户的所有订单"""
        return self.get_multi(session, filters={"user_id": user_id})

    def get_pending_orders(self, session):
        """⏳ 获取待处理订单"""
        statement = select(self.model).where(self.model.status == "pending")
        return session.execute(statement).scalars().all()

    def get_total_amount(self, session, user_id: int) -> float:
        """💰 计算用户订单总金额"""
        statement = (
            select(func.sum(self.model.amount))
            .where(self.model.user_id == user_id)
        )
        result = session.execute(statement).scalar()
        return result or 0.0
```

### 2. 重写基类方法

```python
class CustomUserCRUD(CRUDBase[User, User, User]):
    def __init__(self):
        super().__init__(User)

    def create(self, session, obj_in):
        """➕ 自定义创建逻辑：自动设置创建时间"""
        if isinstance(obj_in, dict):
            obj_in["created_at"] = datetime.now()
        return super().create(session, obj_in)

    def delete(self, session, id, soft=False):
        """🗑️ 自定义删除逻辑：记录删除日志"""
        result = super().delete(session, id, soft)
        # 记录删除日志
        self._log_deletion(session, id)
        return result

    def _log_deletion(self, session, user_id: int):
        """📝 记录删除日志"""
        log = DeletionLog(user_id=user_id, deleted_at=datetime.now())
        session.add(log)
        session.commit()
```

### 3. 组合多个 Mixin

```python
from sqlmodel_crud import CRUDBase, SoftDeleteMixin, RestoreMixin


class AuditableCRUD(CRUDBase, SoftDeleteMixin, RestoreMixin):
    """🛡️ 支持审计和软删除的 CRUD 基类"""

    def create(self, session, obj_in):
        """➕ 创建时自动设置创建者"""
        if isinstance(obj_in, dict):
            obj_in["created_by"] = get_current_user_id()
        return super().create(session, obj_in)

    def update(self, session, id, obj_in):
        """✏️ 更新时自动设置修改者"""
        if isinstance(obj_in, dict):
            obj_in["updated_by"] = get_current_user_id()
            obj_in["updated_at"] = datetime.now()
        return super().update(session, id, obj_in)
```

### 4. 自定义配置

```python
from sqlmodel_crud import GeneratorConfig, load_config

# 方式 1：代码中创建配置
config = GeneratorConfig(
    models_path="src/models",
    output_dir="src/generated",
    generators=["crud", "schemas"],
    crud_suffix="Repository",
    exclude_models=["BaseModel", "AuditLog"],
    # 数据库连接配置
    enable_foreign_keys=True,    # 启用外键约束
    echo_sql=False,              # 打印 SQL 语句（调试）
    pool_size=5,                 # 连接池大小
    max_overflow=10,             # 最大溢出连接
    # 代码生成控制
    generate_model_copy=True,    # 复制模型文件
    format_code=False,           # 自动格式化代码
    backup_before_generate=False, # 生成前备份
)

# 方式 2：使用配置文件（pyproject.toml）
# [tool.sqlmodel-crud]
# models_path = "app/models"
# output_dir = "app/generated"
# generators = ["crud", "schemas"]
# use_async = false  # PyQt 项目通常使用同步模式
# enable_foreign_keys = true
# echo_sql = false
# format_code = true
# backup_before_generate = true

config = load_config()

# 方式 3：环境变量
# SQLMODEL_CRUD_MODELS_PATH=custom/models
# SQLMODEL_CRUD_GENERATORS=crud,schemas
# SQLMODEL_CRUD_ENABLE_FOREIGN_KEYS=true
# SQLMODEL_CRUD_FORMAT_CODE=true
```

---

## ⚠️ 注意事项

### 1. 会话管理

- ✅ 始终使用 `DatabaseManager.get_session()` 或 `get_async_session()` 获取会话
- ✅ 使用上下文管理器确保会话正确关闭
- ❌ 不要在 CRUD 方法内部提交或回滚会话，由上下文管理器处理

```python
# ✅ 正确做法
with db.get_session() as session:
    user = user_crud.create(session, data)  # 自动提交

# ❌ 错误做法
session = db.get_session()  # 没有使用上下文管理器
user = user_crud.create(session, data)
# ⚠️ 会话未关闭，可能导致连接泄漏
```

### 2. 异常处理

- ✅ 始终捕获 `CRUDError` 及其子类，而非原始数据库异常
- ✅ 使用 `get_or_raise` 替代 `get` 当需要确保记录存在时

```python
from sqlmodel_crud import NotFoundError, DuplicateError

try:
    user = user_crud.get_or_raise(session, user_id)
except NotFoundError:
    # 处理记录不存在
    pass
except DuplicateError:
    # 处理重复数据
    pass
```

### 3. 软删除使用

- 📋 模型必须包含 `is_deleted` 或 `deleted_at` 字段才能使用软删除
- 🚫 软删除的记录会被 `get` 和 `get_multi` 自动过滤
- ♻️ 使用 `RestoreMixin` 恢复软删除的记录

```python
class MyModel(SQLModel, table=True):
    # 方式 1：布尔标记
    is_deleted: bool = Field(default=False)

    # 方式 2：时间戳标记（推荐）
    deleted_at: Optional[datetime] = Field(default=None)
```

### 4. 批量操作

- 📊 `create_multi` 默认批次大小为 1000
- 📈 大批量数据导入时，适当调整 `batch_size` 参数
- 🔄 批量操作失败时会自动回滚整个批次

```python
# 📦 大批量导入
users = user_crud.create_multi(session, large_user_list, batch_size=500)
```

### 5. 类型提示

- ✅ 始终为 CRUD 类指定泛型参数以获得完整类型支持
- ✅ 使用 Pydantic 模型作为 Create/Update Schema

```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
    ...
```

### 6. 线程安全

- ✅ `DatabaseManager` 是线程安全的，可在多线程环境中共享
- ✅ `CRUD` 类实例是无状态的，可在多个会话间复用

```python
# 🌍 全局共享
db = DatabaseManager("sqlite:///app.db")
user_crud = UserCRUD()

# 🧵 多线程使用
def worker():
    with db.get_session() as session:
        user = user_crud.get(session, 1)
```

### 7. 外键关联模型

代码生成器支持跨文件的外键关联模型：

```python
# models/unit_project.py
class UnitProject(SQLModel, table=True):
    __tablename__ = "unit_project"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)

# models/construction_quantity.py
class ConstructionQuantity(SQLModel, table=True):
    __tablename__ = "construction_quantity"
    id: Optional[int] = Field(default=None, primary_key=True)
    # 外键引用另一个模型的字段
    unit_project_id: int = Field(foreign_key="unit_project.id", index=True)
    quantity: float = Field(description="工程量数量")
```

**支持的数据库约束**：

| 约束类型 | SQLModel 支持 | 说明 |
|---------|--------------|------|
| 主键 (`PRIMARY KEY`) | ✅ | `Field(primary_key=True)` |
| 外键 (`FOREIGN KEY`) | ✅ | `Field(foreign_key="table.column")` |
| 唯一约束 (`UNIQUE`) | ✅ | `Field(unique=True)` |
| 索引 (`INDEX`) | ✅ | `Field(index=True)` |
| CHECK 约束 | ⚠️ | 需使用 `sa_column` 参数 |
| Trigger | ❌ | 需在数据库迁移脚本中实现 |

### 8. 完整配置选项

| 配置项 | 类型 | 默认值 | 说明 | 环境变量 |
|--------|------|--------|------|----------|
| **基础配置** |
| `models_path` | `str` | `"app/models"` | 模型扫描路径 | `SQLMODEL_CRUD_MODELS_PATH` |
| `output_dir` | `str` | `"app/generated"` | 代码输出目录 | `SQLMODEL_CRUD_OUTPUT_DIR` |
| `generators` | `List[str]` | `["crud"]` | 生成器类型 | `SQLMODEL_CRUD_GENERATORS` |
| `use_async` | `bool` | `False` | 是否生成异步代码 | - |
| **数据库连接** |
| `enable_foreign_keys` | `bool` | `True` | 启用外键约束 | `SQLMODEL_CRUD_ENABLE_FOREIGN_KEYS` |
| `echo_sql` | `bool` | `False` | 打印 SQL 语句 | `SQLMODEL_CRUD_ECHO_SQL` |
| `pool_size` | `int` | `5` | 连接池大小 | `SQLMODEL_CRUD_POOL_SIZE` |
| `max_overflow` | `int` | `10` | 最大溢出连接 | `SQLMODEL_CRUD_MAX_OVERFLOW` |
| **代码生成控制** |
| `generate_model_copy` | `bool` | `True` | 复制模型文件 | `SQLMODEL_CRUD_GENERATE_MODEL_COPY` |
| `generate_data_layer` | `bool` | `True` | 生成数据层文件 | `SQLMODEL_CRUD_GENERATE_DATA_LAYER` |
| `data_layer_db_name` | `str` | `"app.db"` | 数据库文件名 | `SQLMODEL_CRUD_DATA_LAYER_DB_NAME` |
| **代码风格** |
| `format_code` | `bool` | `False` | 自动格式化代码 | `SQLMODEL_CRUD_FORMAT_CODE` |
| `line_length` | `int` | `88` | 代码行长度 | `SQLMODEL_CRUD_LINE_LENGTH` |
| **安全备份** |
| `backup_before_generate` | `bool` | `False` | 生成前备份 | `SQLMODEL_CRUD_BACKUP_BEFORE_GENERATE` |
| `backup_suffix` | `str` | `".bak"` | 备份文件后缀 | `SQLMODEL_CRUD_BACKUP_SUFFIX` |

---

## 📅 维护与更新记录

### 🏷️ 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 0.1.0 | 2026-02-21 | 🎉 初始版本 |
| | | ✅ 实现 CRUDBase 和 AsyncCRUDBase |
| | | 🗑️ 实现软删除和恢复功能 |
| | | 🤖 实现代码生成器 |
| | | ⌨️ 实现 CLI 工具 |
| | | ⚠️ 完整的异常体系 |
| 0.2.0 | 2026-02-23 | 🏗️ 代码生成器架构改革 |
| | | 🔧 强制 CRUD 类继承 CRUDBase/AsyncCRUDBase |
| | | 📦 Schema 模板改用 SQLModel |
| | | 🗑️ 移除 API 生成功能（专注 PyQt） |
| | | 🎯 完全符合 MVP 架构设计 |
| 0.3.0 | 2026-02-23 | 📦 开箱即用功能 |
| | | 🗄️ 自动生成数据层基础设施文件 |
| | | ⚙️ 新增 generate_data_layer 配置选项 |
| | | 📝 自动生成 config.py、database.py、__init__.py |
| 0.4.0 | 2026-02-23 | 🎯 专为 PyQt 桌面应用优化 |
| | | 🗑️ 移除 Schema 层（Create/Update/Response） |
| | | 📦 直接使用原始 SQLModel 模型类 |
| | | 🔧 简化 CRUD 使用方式（字典传参） |
| 0.4.1 | 2026-02-23 | 🐛 修复外键解析错误 |
| | | 🔧 添加 `NoReferencedTableError` 异常处理 |
| | | 🔄 跨文件外键引用现在可以正常工作 |
| 1.0.0 | 2026-03-14 | ⚙️ 增强 GeneratorConfig 配置选项 |
| | | 🔗 添加外键约束、SQL 调试等数据库连接配置 |
| | | 🎨 添加代码格式化、文件备份功能 |
| | | 📝 支持通过环境变量配置所有选项 |

### 🚀 开发计划

- [ ] 🗄️ 支持更多数据库（Oracle、SQL Server）
- [ ] 💾 添加缓存层支持（Redis）
- [ ] 🔗 实现关联查询优化
- [ ] 📝 添加更多代码生成模板
- [ ] 🔄 支持数据库迁移集成

---

## 📄 许可证

本项目为个人使用的内部基础设施代码，请遵循团队内部的代码使用规范。

---

**📋 文档版本**: 1.0
**📅 最后更新**: 2026年3月14日
**👤 作者**: LucYang 杨艺斌
**🔧 最新变更**: 增强 GeneratorConfig 配置选项，添加外键约束、SQL 调试等数据库连接配置，可以交付。
