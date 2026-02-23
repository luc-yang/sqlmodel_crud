"""
DatabaseManager 测试模块

测试 DatabaseManager 类的所有功能，包括同步和异步模式。
使用内存 SQLite 数据库进行测试。
"""

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel, Field
from typing import Optional

from sqlmodel_crud.database import DatabaseManager

# =============================================================================
# 测试模型定义
# =============================================================================


class DatabaseTestModel(SQLModel, table=True):
    """测试模型

    用于测试数据库表创建和操作的简单模型。

    Attributes:
        id: 主键 ID，自动递增
        name: 名称字段
        value: 数值字段
    """

    __tablename__ = "database_test_model"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    value: int = 0


# =============================================================================
# 同步测试类
# =============================================================================


class TestDatabaseManagerSync:
    """DatabaseManager 同步模式测试类

    测试 DatabaseManager 在同步模式下的所有功能。
    """

    def test_create_engine(self):
        """测试 create_engine 方法创建同步引擎

        验证 create_engine 方法能够正确创建 SQLAlchemy 同步引擎实例。
        """
        db = DatabaseManager("sqlite:///:memory:")
        engine = db.create_engine()

        assert engine is not None
        assert isinstance(engine, Engine)
        db.close()

    def test_create_engine_returns_same_instance(self):
        """测试多次调用返回同一实例

        验证多次调用 create_engine 返回的是同一个引擎实例（单例模式）。
        """
        db = DatabaseManager("sqlite:///:memory:")
        engine1 = db.create_engine()
        engine2 = db.create_engine()

        assert engine1 is engine2
        db.close()

    def test_get_session_context_manager(self):
        """测试 get_session 上下文管理器正常工作

        验证 get_session 上下文管理器能够正确创建和关闭会话。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_engine()

        with db.get_session() as session:
            # 验证会话可以执行查询
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        db.close()

    def test_get_session_auto_commit(self):
        """测试会话自动提交

        验证在上下文管理器正常退出时会话会自动提交事务。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()

        # 创建测试表
        SQLModel.metadata.create_all(bind=db.create_engine())

        with db.get_session() as session:
            # 插入数据
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)"
                )
            )
            session.execute(text("INSERT INTO test_table (name) VALUES ('test')"))

        # 新会话验证数据已提交
        with db.get_session() as session:
            result = session.execute(text("SELECT name FROM test_table WHERE id = 1"))
            assert result.scalar() == "test"

        db.close()

    def test_get_session_rollback_on_error(self):
        """测试出错时自动回滚

        验证在上下文管理器中发生异常时会话会自动回滚事务。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()

        # 创建测试表
        SQLModel.metadata.create_all(bind=db.create_engine())

        try:
            with db.get_session() as session:
                session.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)"
                    )
                )
                session.execute(
                    text("INSERT INTO test_table (name) VALUES ('before_error')")
                )
                raise ValueError("测试异常")
        except ValueError:
            pass

        # 新会话验证数据未提交（已回滚）
        with db.get_session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM test_table"))
            count = result.scalar()
            # 表已创建但数据未提交
            assert count == 0

        db.close()

    def test_create_tables(self):
        """测试 create_tables 方法创建表

        验证 create_tables 方法能够根据 SQLModel 元数据创建数据库表。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()

        # 验证表已创建
        with db.get_session() as session:
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='database_test_model'"
                )
            )
            assert result.scalar() == "database_test_model"

        db.close()

    def test_drop_tables(self):
        """测试 drop_tables 方法删除表

        验证 drop_tables 方法能够删除所有由 SQLModel 管理的表。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()

        # 验证表已创建
        with db.get_session() as session:
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='database_test_model'"
                )
            )
            assert result.scalar() == "database_test_model"

        # 删除表
        db.drop_tables()

        # 验证表已删除
        with db.get_session() as session:
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='database_test_model'"
                )
            )
            assert result.scalar() is None

        db.close()

    def test_is_async_false_for_sync_url(self):
        """测试同步 URL 的 is_async 返回 False

        验证对于同步数据库 URL，is_async 属性返回 False。
        """
        db = DatabaseManager("sqlite:///:memory:")
        assert db.is_async is False

        db2 = DatabaseManager("postgresql://user:pass@localhost/db")
        assert db2.is_async is False

        db3 = DatabaseManager("mysql+pymysql://user:pass@localhost/db")
        assert db3.is_async is False

    def test_close(self):
        """测试 close 方法关闭引擎

        验证 close 方法能够正确关闭引擎并清理资源。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_engine()

        # 验证引擎已创建
        assert db._engine is not None
        assert db._session_maker is not None

        # 关闭引擎
        db.close()

        # 验证引擎已清理
        assert db._engine is None
        assert db._session_maker is None


# =============================================================================
# 异步测试类
# =============================================================================


class TestDatabaseManagerAsync:
    """DatabaseManager 异步模式测试类

    测试 DatabaseManager 在异步模式下的所有功能。
    """

    def test_create_async_engine(self):
        """测试 create_async_engine 方法创建异步引擎

        验证 create_async_engine 方法能够正确创建 SQLAlchemy 异步引擎实例。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        engine = db.create_async_engine()

        assert engine is not None
        assert isinstance(engine, AsyncEngine)

    def test_create_async_engine_returns_same_instance(self):
        """测试多次调用返回同一实例

        验证多次调用 create_async_engine 返回的是同一个引擎实例（单例模式）。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        engine1 = db.create_async_engine()
        engine2 = db.create_async_engine()

        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_get_async_session_context_manager(self):
        """测试 get_async_session 上下文管理器

        验证 get_async_session 异步上下文管理器能够正确创建和关闭会话。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        db.create_async_engine()

        async with db.get_async_session() as session:
            # 验证会话可以执行查询
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_get_async_session_auto_commit(self):
        """测试异步会话自动提交

        验证在异步上下文管理器正常退出时会话会自动提交事务。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await db.create_tables_async()

        async with db.get_async_session() as session:
            # 插入数据
            await session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)"
                )
            )
            await session.execute(text("INSERT INTO test_table (name) VALUES ('test')"))

        # 新会话验证数据已提交
        async with db.get_async_session() as session:
            result = await session.execute(
                text("SELECT name FROM test_table WHERE id = 1")
            )
            assert result.scalar() == "test"

        await db.close_async()

    @pytest.mark.asyncio
    async def test_get_async_session_rollback_on_error(self):
        """测试异步出错时自动回滚

        验证在异步上下文管理器中发生异常时会话会自动回滚事务。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await db.create_tables_async()

        try:
            async with db.get_async_session() as session:
                await session.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)"
                    )
                )
                await session.execute(
                    text("INSERT INTO test_table (name) VALUES ('before_error')")
                )
                raise ValueError("测试异常")
        except ValueError:
            pass

        # 新会话验证数据未提交（已回滚）
        async with db.get_async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM test_table"))
            count = result.scalar()
            # 表已创建但数据未提交
            assert count == 0

        await db.close_async()

    @pytest.mark.asyncio
    async def test_create_tables_async(self):
        """测试异步创建表

        验证 create_tables_async 方法能够异步创建数据库表。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await db.create_tables_async()

        # 验证表已创建
        async with db.get_async_session() as session:
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='database_test_model'"
                )
            )
            assert result.scalar() == "database_test_model"

        await db.close_async()

    @pytest.mark.asyncio
    async def test_drop_tables_async(self):
        """测试异步删除表

        验证 drop_tables_async 方法能够异步删除所有由 SQLModel 管理的表。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await db.create_tables_async()

        # 验证表已创建
        async with db.get_async_session() as session:
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='database_test_model'"
                )
            )
            assert result.scalar() == "database_test_model"

        # 删除表
        await db.drop_tables_async()

        # 验证表已删除
        async with db.get_async_session() as session:
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='database_test_model'"
                )
            )
            assert result.scalar() is None

        await db.close_async()

    def test_is_async_true_for_async_url(self):
        """测试异步 URL 的 is_async 返回 True

        验证对于异步数据库 URL，is_async 属性返回 True。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        assert db.is_async is True

        db2 = DatabaseManager("postgresql+asyncpg://user:pass@localhost/db")
        assert db2.is_async is True

        db3 = DatabaseManager("mysql+aiomysql://user:pass@localhost/db")
        assert db3.is_async is True

        db4 = DatabaseManager("mysql+asyncmy://user:pass@localhost/db")
        assert db4.is_async is True

    def test_close_async(self):
        """测试异步关闭引擎

        验证 close_async 方法能够正确关闭异步引擎并清理资源。
        """
        import asyncio

        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        db.create_async_engine()

        # 验证引擎已创建
        assert db._async_engine is not None
        assert db._async_session_maker is not None

        # 关闭引擎
        asyncio.run(db.close_async())

        # 验证引擎已清理
        assert db._async_engine is None
        assert db._async_session_maker is None


# =============================================================================
# 上下文管理器测试类
# =============================================================================


class TestDatabaseManagerContextManager:
    """DatabaseManager 上下文管理器测试类

    测试 DatabaseManager 作为上下文管理器的功能。
    """

    def test_sync_context_manager(self):
        """测试同步上下文管理器

        验证 DatabaseManager 可以作为同步上下文管理器使用，
        直接提供会话对象。
        """
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()

        with db as session:
            # 验证会话可以执行查询
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # 验证会话上下文已退出（引擎仍然存在，需要手动关闭）
        assert db._engine is not None
        db.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器

        验证 DatabaseManager 可以作为异步上下文管理器使用，
        直接提供异步会话对象。
        """
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await db.create_tables_async()

        async with db as session:
            # 验证会话可以执行查询
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # 验证会话上下文已退出（引擎仍然存在，需要手动关闭）
        assert db._async_engine is not None
        await db.close_async()
