"""数据库连接管理模块"""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session as SASession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import SQLModel

from .exceptions import DatabaseError


class DatabaseManager:
    """数据库连接管理器"""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        connect_args: Optional[dict] = None,
    ):
        """初始化数据库管理器"""
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping
        self.connect_args = connect_args or {}

        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[sessionmaker] = None
        self._async_session_maker: Optional[async_sessionmaker] = None

    @property
    def is_async(self) -> bool:
        """判断是否为异步数据库URL"""
        return any(
            driver in self.database_url
            for driver in ["+aiosqlite", "+asyncpg", "+aiomysql", "+asyncmy"]
        )

    def create_engine(self) -> Engine:
        """创建同步数据库引擎"""
        if self._engine is not None:
            return self._engine

        try:

            engine_kwargs = {
                "echo": self.echo,
                "pool_pre_ping": self.pool_pre_ping,
            }

            if self.database_url.startswith("sqlite"):
                self.connect_args.setdefault("check_same_thread", False)

                from sqlalchemy.pool import StaticPool

                engine_kwargs["poolclass"] = StaticPool
            else:

                engine_kwargs["pool_size"] = self.pool_size
                engine_kwargs["max_overflow"] = self.max_overflow

            engine_kwargs["connect_args"] = self.connect_args

            self._engine = create_engine(
                self.database_url,
                **engine_kwargs,
            )

            self._session_maker = sessionmaker(
                autocommit=False, autoflush=False, bind=self._engine
            )

            return self._engine

        except Exception as e:
            raise DatabaseError(
                "创建数据库引擎失败", original=e, operation="create_engine"
            )

    def create_async_engine(self) -> AsyncEngine:
        """创建异步数据库引擎"""
        if self._async_engine is not None:
            return self._async_engine

        try:

            engine_kwargs = {
                "echo": self.echo,
                "pool_pre_ping": self.pool_pre_ping,
            }

            if self.database_url.startswith("sqlite"):

                from sqlalchemy.pool import StaticPool

                engine_kwargs["poolclass"] = StaticPool
            else:

                engine_kwargs["pool_size"] = self.pool_size
                engine_kwargs["max_overflow"] = self.max_overflow

            self._async_engine = create_async_engine(
                self.database_url,
                **engine_kwargs,
            )

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
        """获取同步数据库会话（上下文管理器）"""
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
        """获取异步数据库会话（异步上下文管理器）"""
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
        """创建所有数据库表"""
        try:
            engine = self.create_engine()
            SQLModel.metadata.create_all(bind=engine)
        except Exception as e:
            raise DatabaseError(
                "创建数据库表失败", original=e, operation="create_tables"
            )

    async def create_tables_async(self) -> None:
        """异步创建所有数据库表"""
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
        """删除所有数据库表"""
        try:
            engine = self.create_engine()
            SQLModel.metadata.drop_all(bind=engine)
        except Exception as e:
            raise DatabaseError("删除数据库表失败", original=e, operation="drop_tables")

    async def drop_tables_async(self) -> None:
        """异步删除所有数据库表"""
        try:
            engine = self.create_async_engine()
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)
        except Exception as e:
            raise DatabaseError(
                "异步删除数据库表失败", original=e, operation="drop_tables_async"
            )

    def close(self) -> None:
        """关闭同步数据库连接"""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_maker = None

    async def close_async(self) -> None:
        """关闭异步数据库连接"""
        if self._async_engine is not None:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_maker = None

    def __enter__(self):
        """上下文管理器入口（同步）"""
        self._session_context = self.get_session()
        return self._session_context.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口（同步）"""
        return self._session_context.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._async_session_context = self.get_async_session()
        return await self._async_session_context.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        return await self._async_session_context.__aexit__(exc_type, exc_val, exc_tb)
