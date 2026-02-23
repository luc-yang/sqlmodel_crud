"""
数据库连接管理模块

提供数据库连接管理器，支持灵活的数据库配置和会话管理。
支持同步和异步两种模式。
"""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session as SASession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import SQLModel

from .exceptions import DatabaseError


class DatabaseManager:
    """数据库连接管理器

    管理数据库连接、引擎创建和会话生命周期。
    支持同步和异步两种模式，提供上下文管理器简化会话使用。

    Attributes:
        database_url: 数据库连接URL
        echo: 是否打印SQL语句（调试用）
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出数
        engine: SQLAlchemy 引擎实例（延迟创建）
        async_engine: SQLAlchemy 异步引擎实例（延迟创建）

    示例:
        >>> # 同步模式
        >>> db = DatabaseManager("sqlite:///example.db")
        >>> with db.get_session() as session:
        ...     result = session.execute(select(User)).scalars().all()
        ...
        >>> # 异步模式
        >>> db = DatabaseManager("sqlite+aiosqlite:///example.db")
        >>> async with db.get_async_session() as session:
        ...     result = await session.execute(select(User))
        ...     users = result.scalars().all()
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        connect_args: Optional[dict] = None,
    ):
        """初始化数据库管理器

        Args:
            database_url: 数据库连接URL
                支持的格式：
                - SQLite: sqlite:///path/to/db.sqlite
                - SQLite (异步): sqlite+aiosqlite:///path/to/db.sqlite
                - PostgreSQL: postgresql://user:pass@localhost/dbname
                - PostgreSQL (异步): postgresql+asyncpg://user:pass@localhost/dbname
                - MySQL: mysql+pymysql://user:pass@localhost/dbname
                - MySQL (异步): mysql+aiomysql://user:pass@localhost/dbname
            echo: 是否打印SQL语句（调试用）
            pool_size: 连接池大小
            max_overflow: 连接池最大溢出数
            pool_pre_ping: 是否在获取连接前测试连接是否有效
            connect_args: 额外的连接参数
        """
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping
        self.connect_args = connect_args or {}

        # 引擎实例（延迟创建）
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[sessionmaker] = None
        self._async_session_maker: Optional[async_sessionmaker] = None

    @property
    def is_async(self) -> bool:
        """判断是否为异步数据库URL

        Returns:
            如果是异步URL返回 True，否则返回 False
        """
        return any(
            driver in self.database_url
            for driver in ["+aiosqlite", "+asyncpg", "+aiomysql", "+asyncmy"]
        )

    def create_engine(self) -> Engine:
        """创建同步数据库引擎

        创建并配置 SQLAlchemy 同步引擎。
        如果引擎已存在则返回现有实例。

        Returns:
            SQLAlchemy Engine 实例

        Raises:
            DatabaseError: 引擎创建失败时抛出
        """
        if self._engine is not None:
            return self._engine

        try:
            # 构建引擎参数
            engine_kwargs = {
                "echo": self.echo,
                "pool_pre_ping": self.pool_pre_ping,
            }

            # SQLite 特殊处理
            if self.database_url.startswith("sqlite"):
                self.connect_args.setdefault("check_same_thread", False)
                # SQLite 使用 StaticPool，不支持 pool_size 和 max_overflow
                from sqlalchemy.pool import StaticPool

                engine_kwargs["poolclass"] = StaticPool
            else:
                # 其他数据库使用连接池参数
                engine_kwargs["pool_size"] = self.pool_size
                engine_kwargs["max_overflow"] = self.max_overflow

            engine_kwargs["connect_args"] = self.connect_args

            self._engine = create_engine(
                self.database_url,
                **engine_kwargs,
            )

            # 创建会话工厂
            self._session_maker = sessionmaker(
                autocommit=False, autoflush=False, bind=self._engine
            )

            return self._engine

        except Exception as e:
            raise DatabaseError(
                "创建数据库引擎失败", original=e, operation="create_engine"
            )

    def create_async_engine(self) -> AsyncEngine:
        """创建异步数据库引擎

        创建并配置 SQLAlchemy 异步引擎。
        如果引擎已存在则返回现有实例。

        Returns:
            SQLAlchemy AsyncEngine 实例

        Raises:
            DatabaseError: 引擎创建失败时抛出
        """
        if self._async_engine is not None:
            return self._async_engine

        try:
            # 构建引擎参数
            engine_kwargs = {
                "echo": self.echo,
                "pool_pre_ping": self.pool_pre_ping,
            }

            # SQLite 异步特殊处理
            if self.database_url.startswith("sqlite"):
                # SQLite 使用 StaticPool，不支持 pool_size 和 max_overflow
                from sqlalchemy.pool import StaticPool

                engine_kwargs["poolclass"] = StaticPool
            else:
                # 其他数据库使用连接池参数
                engine_kwargs["pool_size"] = self.pool_size
                engine_kwargs["max_overflow"] = self.max_overflow

            self._async_engine = create_async_engine(
                self.database_url,
                **engine_kwargs,
            )

            # 创建异步会话工厂
            self._async_session_maker = sessionmaker(
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                bind=self._async_engine,
            )

            return self._async_engine

        except Exception as e:
            raise DatabaseError(
                "创建异步数据库引擎失败",
                original=e,
                operation="create_async_engine",
            )

    @contextmanager
    def get_session(self) -> Generator[SASession, None, None]:
        """获取同步数据库会话（上下文管理器）

        提供自动管理生命周期的数据库会话。
        会话会在退出上下文时自动关闭，发生异常时自动回滚。

        Yields:
            SQLAlchemy Session 实例

        Raises:
            DatabaseError: 会话创建失败时抛出

        示例:
            >>> with db.get_session() as session:
            ...     # 查询用户
            ...     result = session.execute(select(User).where(User.id == 1))
            ...     user = result.scalar_one_or_none()
            ...     if user:
            ...         print(f"找到用户: {user.name}")
        """
        if self._session_maker is None:
            self.create_engine()

        session = self._session_maker()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步数据库会话（异步上下文管理器）

        提供自动管理生命周期的异步数据库会话。
        会话会在退出上下文时自动关闭，发生异常时自动回滚。

        Yields:
            SQLAlchemy AsyncSession 实例

        Raises:
            DatabaseError: 会话创建失败时抛出

        示例:
            >>> async with db.get_async_session() as session:
            ...     result = await session.execute(select(User))
            ...     users = result.scalars().all()
        """
        if self._async_session_maker is None:
            self.create_async_engine()

        session = self._async_session_maker()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    def create_tables(self) -> None:
        """创建所有数据库表

        根据 SQLModel 元数据创建所有未存在的表。
        注意：不会更新已存在的表结构。

        Raises:
            DatabaseError: 表创建失败时抛出

        示例:
            >>> db = DatabaseManager("sqlite:///example.db")
            >>> db.create_tables()
        """
        try:
            engine = self.create_engine()
            SQLModel.metadata.create_all(bind=engine)
        except Exception as e:
            raise DatabaseError(
                "创建数据库表失败", original=e, operation="create_tables"
            )

    async def create_tables_async(self) -> None:
        """异步创建所有数据库表

        根据 SQLModel 元数据异步创建所有未存在的表。

        Raises:
            DatabaseError: 表创建失败时抛出

        示例:
            >>> db = DatabaseManager("sqlite+aiosqlite:///example.db")
            >>> await db.create_tables_async()
        """
        try:
            engine = self.create_async_engine()
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
        except Exception as e:
            raise DatabaseError(
                "异步创建数据库表失败",
                original=e,
                operation="create_tables_async",
            )

    def drop_tables(self) -> None:
        """删除所有数据库表

        删除所有由 SQLModel 管理的表。
        警告：此操作会删除数据，请谨慎使用！

        Raises:
            DatabaseError: 表删除失败时抛出

        示例:
            >>> db = DatabaseManager("sqlite:///example.db")
            >>> db.drop_tables()  # 谨慎使用！
        """
        try:
            engine = self.create_engine()
            SQLModel.metadata.drop_all(bind=engine)
        except Exception as e:
            raise DatabaseError("删除数据库表失败", original=e, operation="drop_tables")

    async def drop_tables_async(self) -> None:
        """异步删除所有数据库表

        异步删除所有由 SQLModel 管理的表。
        警告：此操作会删除数据，请谨慎使用！

        Raises:
            DatabaseError: 表删除失败时抛出

        示例:
            >>> db = DatabaseManager("sqlite+aiosqlite:///example.db")
            >>> await db.drop_tables_async()  # 谨慎使用！
        """
        try:
            engine = self.create_async_engine()
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)
        except Exception as e:
            raise DatabaseError(
                "异步删除数据库表失败", original=e, operation="drop_tables_async"
            )

    def close(self) -> None:
        """关闭同步数据库连接

        关闭引擎和清理所有连接池资源。
        在应用程序关闭时调用。

        示例:
            >>> db.close()
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_maker = None

    async def close_async(self) -> None:
        """关闭异步数据库连接

        关闭异步引擎和清理所有连接池资源。
        在应用程序关闭时调用。

        示例:
            >>> await db.close_async()
        """
        if self._async_engine is not None:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_maker = None

    def __enter__(self):
        """上下文管理器入口（同步）

        支持使用 with 语句直接获取会话：

        示例:
            >>> with DatabaseManager("sqlite:///db.sqlite") as session:
            ...     result = session.execute(select(User)).scalars().all()
        """
        self._session_context = self.get_session()
        return self._session_context.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口（同步）"""
        return self._session_context.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        """异步上下文管理器入口

        支持使用 async with 语句直接获取会话：

        示例:
            >>> async with DatabaseManager("sqlite+aiosqlite:///db.sqlite") as session:
            ...     result = await session.execute(select(User))
            ...     users = result.scalars().all()
        """
        self._async_session_context = self.get_async_session()
        return await self._async_session_context.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        return await self._async_session_context.__aexit__(exc_type, exc_val, exc_tb)
