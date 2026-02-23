"""
测试配置和共享 fixtures

提供测试所需的模型定义、数据库连接和 CRUD 实例 fixtures。
支持同步和异步两种测试模式。
"""

from datetime import datetime
from typing import Optional

import pytest
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from sqlmodel_crud.database import DatabaseManager
from sqlmodel_crud.base import CRUDBase, AsyncCRUDBase, RestoreMixin

# =============================================================================
# 测试模型定义
# =============================================================================


class TestUser(SQLModel, table=True):
    """测试用户模型

    用于测试 CRUD 基础功能的用户实体模型。
    包含常见的用户字段：基本信息、状态和时间戳。

    Attributes:
        id: 主键 ID，自动递增
        name: 用户名，必填
        email: 邮箱地址，必填
        age: 年龄，可选
        is_active: 是否激活，默认为 True
        created_at: 创建时间，自动设置为当前时间
    """

    __tablename__ = "test_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    age: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # 关系定义
    items: list["TestItem"] = Relationship(back_populates="owner")


class TestItem(SQLModel, table=True):
    """测试物品模型

    用于测试关联关系和 CRUD 功能的物品实体模型。
    与用户模型建立外键关联。

    Attributes:
        id: 主键 ID，自动递增
        name: 物品名称，必填
        description: 物品描述，可选
        price: 物品价格，必填
        owner_id: 外键，关联到 TestUser
    """

    __tablename__ = "test_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    price: float = Field(default=0.0)
    owner_id: Optional[int] = Field(default=None, foreign_key="test_users.id")

    # 关系定义
    owner: Optional[TestUser] = Relationship(back_populates="items")


class SoftDeleteUser(SQLModel, table=True):
    """软删除测试用户模型

    用于测试软删除和恢复功能的用户实体模型。
    包含软删除所需的特殊字段。

    Attributes:
        id: 主键 ID，自动递增
        name: 用户名，必填
        email: 邮箱地址，必填
        is_deleted: 是否已删除标记，默认为 False
        deleted_at: 删除时间，可选
    """

    __tablename__ = "soft_delete_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# =============================================================================
# 同步 Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def db_manager():
    """同步数据库管理器 fixture

    创建使用内存 SQLite 的数据库管理器，并在测试结束后清理资源。

    Yields:
        DatabaseManager: 配置好的同步数据库管理器实例

    Example:
        >>> def test_example(db_manager):
        ...     db_manager.create_tables()
        ...     # 执行测试...
    """
    manager = DatabaseManager(
        database_url="sqlite:///:memory:",
        echo=False,
    )
    yield manager
    manager.close()


@pytest.fixture(scope="function")
def session(db_manager):
    """同步数据库会话 fixture

    提供已创建好表结构的数据库会话，测试结束后自动回滚。

    Args:
        db_manager: 数据库管理器 fixture

    Yields:
        Session: SQLAlchemy 同步会话实例

    Example:
        >>> def test_example(session):
        ...     user = TestUser(name="张三")
        ...     session.add(user)
        ...     session.commit()
    """
    # 创建所有表
    db_manager.create_tables()

    # 创建会话
    with db_manager.get_session() as sess:
        yield sess


@pytest.fixture(scope="function")
def test_user_crud():
    """TestUser CRUD 实例 fixture

    提供 TestUser 模型的 CRUD 操作实例。

    Returns:
        CRUDBase[TestUser, dict, dict]: TestUser 的 CRUD 实例

    Example:
        >>> def test_example(session, test_user_crud):
        ...     user = test_user_crud.create(session, {"name": "张三", "email": "zhang@test.com"})
    """
    return CRUDBase(TestUser)


@pytest.fixture(scope="function")
def test_item_crud():
    """TestItem CRUD 实例 fixture

    提供 TestItem 模型的 CRUD 操作实例。

    Returns:
        CRUDBase[TestItem, dict, dict]: TestItem 的 CRUD 实例

    Example:
        >>> def test_example(session, test_item_crud):
        ...     item = test_item_crud.create(session, {"name": "物品1", "price": 100.0})
    """
    return CRUDBase(TestItem)


@pytest.fixture(scope="function")
def soft_delete_user_crud():
    """SoftDeleteUser CRUD 实例 fixture（带 RestoreMixin）

    提供 SoftDeleteUser 模型的 CRUD 操作实例，支持软删除恢复功能。

    Returns:
        SoftDeleteUserCRUD: 带有 RestoreMixin 的 SoftDeleteUser CRUD 实例

    Example:
        >>> def test_example(session, soft_delete_user_crud):
        ...     user = soft_delete_user_crud.create(session, {"name": "张三", "email": "zhang@test.com"})
        ...     soft_delete_user_crud.delete(session, user.id, soft=True)
        ...     restored = soft_delete_user_crud.restore(session, user.id)
    """

    class SoftDeleteUserCRUD(CRUDBase, RestoreMixin):
        """支持恢复功能的 SoftDeleteUser CRUD 类"""

        def __init__(self):
            super().__init__(SoftDeleteUser)

    return SoftDeleteUserCRUD()


# =============================================================================
# 异步 Fixtures
# =============================================================================


@pytest.fixture(scope="function")
async def async_db_manager():
    """异步数据库管理器 fixture

    创建使用异步内存 SQLite 的数据库管理器，并在测试结束后清理资源。

    Yields:
        DatabaseManager: 配置好的异步数据库管理器实例

    Example:
        >>> async def test_example(async_db_manager):
        ...     await async_db_manager.create_tables_async()
        ...     # 执行测试...
    """
    manager = DatabaseManager(
        database_url="sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    yield manager
    await manager.close_async()


@pytest.fixture(scope="function")
async def async_session(async_db_manager):
    """异步数据库会话 fixture

    提供已创建好表结构的异步数据库会话，测试结束后自动回滚。

    Args:
        async_db_manager: 异步数据库管理器 fixture

    Yields:
        AsyncSession: SQLAlchemy 异步会话实例

    Example:
        >>> async def test_example(async_session):
        ...     user = TestUser(name="张三")
        ...     async_session.add(user)
        ...     await async_session.commit()
    """
    # 创建所有表
    await async_db_manager.create_tables_async()

    # 创建异步会话
    async with async_db_manager.get_async_session() as sess:
        yield sess


@pytest.fixture(scope="function")
def async_test_user_crud():
    """异步 TestUser CRUD 实例 fixture

    提供 TestUser 模型的异步 CRUD 操作实例。

    Returns:
        AsyncCRUDBase[TestUser, dict, dict]: TestUser 的异步 CRUD 实例

    Example:
        >>> async def test_example(async_session, async_test_user_crud):
        ...     user = await async_test_user_crud.create(async_session, {"name": "张三"})
    """
    return AsyncCRUDBase(TestUser)


@pytest.fixture(scope="function")
def async_test_item_crud():
    """异步 TestItem CRUD 实例 fixture

    提供 TestItem 模型的异步 CRUD 操作实例。

    Returns:
        AsyncCRUDBase[TestItem, dict, dict]: TestItem 的异步 CRUD 实例

    Example:
        >>> async def test_example(async_session, async_test_item_crud):
        ...     item = await async_test_item_crud.create(async_session, {"name": "物品1"})
    """
    return AsyncCRUDBase(TestItem)


@pytest.fixture(scope="function")
def async_soft_delete_user_crud():
    """异步 SoftDeleteUser CRUD 实例 fixture（带 AsyncRestoreMixin）

    提供 SoftDeleteUser 模型的异步 CRUD 操作实例，支持软删除恢复功能。

    Returns:
        AsyncSoftDeleteUserCRUD: 带有 AsyncRestoreMixin 的异步 SoftDeleteUser CRUD 实例

    Example:
        >>> async def test_example(async_session, async_soft_delete_user_crud):
        ...     user = await async_soft_delete_user_crud.create(async_session, {"name": "张三"})
        ...     await async_soft_delete_user_crud.delete(async_session, user.id, soft=True)
        ...     restored = await async_soft_delete_user_crud.restore(async_session, user.id)
    """
    from sqlmodel_crud.base import AsyncRestoreMixin

    class AsyncSoftDeleteUserCRUD(AsyncCRUDBase, AsyncRestoreMixin):
        """支持恢复功能的异步 SoftDeleteUser CRUD 类"""

        def __init__(self):
            super().__init__(SoftDeleteUser)

    return AsyncSoftDeleteUserCRUD()
