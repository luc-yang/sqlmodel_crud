# coding:utf-8
"""
数据库初始化模块

提供数据库初始化功能，包括表创建、触发器创建等。
该文件由 SQLModel CRUD 生成器自动生成。

生成时间: 2026-02-27 13:26:43
警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""

from typing import Optional
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text, event

from .config import DatabaseConfig, default_config


class DatabaseInitializer:
    """数据库初始化器

    负责数据库表的创建、触发器的创建等初始化操作。

    Attributes:
        db_config: 数据库配置实例
        _engine: SQLAlchemy 引擎实例（延迟创建）

    示例:
        >>> initializer = DatabaseInitializer()
        >>> initializer.init_database()
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """初始化数据库初始化器

        Args:
            db_config: 数据库配置，默认使用 default_config
        """
        self.db_config = db_config or default_config
        self._engine = None  # 延迟创建引擎

    def get_engine(self):
        """获取数据库引擎（延迟创建）

        首次访问时创建引擎，确保配置已经设置。

        Returns:
            SQLAlchemy Engine 实例
        """
        if self._engine is None:
            self._engine = create_engine(
                self.db_config.database_url,
                echo=False,
                connect_args={"check_same_thread": False},
                pool_size=5,
                max_overflow=10,
            )
            # 启用外键约束
            @event.listens_for(self._engine, "connect")
            def enable_foreign_keys(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")
                cursor.close()
        return self._engine

    def create_tables(self, engine=None) -> None:
        """创建所有数据库表

        根据 SQLModel 元数据创建所有未存在的表。

        Args:
            engine: 数据库引擎，如果不提供则自动创建

        示例:
            >>> initializer = DatabaseInitializer()
            >>> initializer.create_tables()
        """
        if engine is None:
            engine = self.get_engine()

        SQLModel.metadata.create_all(bind=engine)

    def drop_tables(self, engine=None) -> None:
        """删除所有数据库表

        删除所有由 SQLModel 管理的表。
        警告：此操作会删除数据，请谨慎使用！

        Args:
            engine: 数据库引擎，如果不提供则自动创建

        示例:
            >>> initializer = DatabaseInitializer()
            >>> initializer.drop_tables()  # 谨慎使用！
        """
        if engine is None:
            engine = self.get_engine()

        SQLModel.metadata.drop_all(bind=engine)

    def init_database(self, engine=None) -> None:
        """初始化数据库

        执行完整的数据库初始化流程：
        1. 确保数据库目录存在
        2. 创建所有表

        注意：updated_at 字段通过 SQLAlchemy 的 onupdate 参数自动更新，无需触发器。

        Args:
            engine: 数据库引擎，如果不提供则自动创建

        示例:
            >>> initializer = DatabaseInitializer()
            >>> initializer.init_database()
        """
        # 确保目录存在
        self.db_config.ensure_directory()

        # 创建引擎（如果未提供）
        if engine is None:
            engine = self.get_engine()

        # 创建表
        self.create_tables(engine)

    def is_initialized(self, engine=None) -> bool:
        """检查数据库是否已初始化

        Args:
            engine: 数据库引擎，如果不提供则自动创建

        Returns:
            如果数据库已初始化返回 True，否则返回 False
        """
        if not self.db_config.exists():
            return False

        if engine is None:
            engine = self.get_engine()

        try:
            with Session(engine) as session:
                # 检查是否存在任意一个模型表
                result = session.exec(
                    text("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                )
                return result.first() is not None
        except Exception:
            return False


# 全局初始化函数
def init_database(db_config: Optional[DatabaseConfig] = None) -> None:
    """初始化数据库（全局函数）

    这是应用启动时调用的主要函数。

    Args:
        db_config: 数据库配置，默认使用 default_config

    示例:
        >>> # 在应用启动时调用
        >>> init_database()
    """
    initializer = DatabaseInitializer(db_config)
    initializer.init_database()


class DatabaseManager:
    """数据库管理器

    提供统一的数据库会话管理，支持作为上下文管理器使用。
    推荐在应用中使用单例模式管理数据库连接。

    支持延迟引擎创建和配置更新，解决导入顺序导致的多数据库文件问题。

    Attributes:
        db_config: 数据库配置实例
        engine: SQLAlchemy 引擎实例（延迟创建）

    示例:
        >>> # 方式1：使用默认配置
        >>> db = DatabaseManager()
        >>> with db.get_session() as session:
        ...     # 执行数据库操作
        ...     pass
        >>>
        >>> # 方式2：使用自定义配置
        >>> config = DatabaseConfig(db_name="myapp.db")
        >>> db = DatabaseManager(config)
        >>> with db.get_session() as session:
        ...     user_crud = UserCRUD()
        ...     user = user_crud.create(session, UserCreate(name="张三"))
        >>>
        >>> # 方式3：应用启动时更新配置
        >>> db = DatabaseManager()
        >>> db.set_config(DatabaseConfig(db_name="myapp.db"))
    """

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls, db_config: Optional[DatabaseConfig] = None):
        """单例模式实现

        确保应用中只有一个 DatabaseManager 实例。

        Args:
            db_config: 数据库配置，仅在首次创建时生效

        Returns:
            DatabaseManager 单例实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """初始化数据库管理器

        Args:
            db_config: 数据库配置，首次传入会保存，后续传入会更新
        """
        # 避免重复初始化
        if self._initialized:
            # 如果传入了新配置，更新配置并重置引擎
            if db_config is not None:
                self.db_config = db_config
                self._engine = None  # 重置引擎，下次访问时重新创建
            return

        self.db_config = db_config or default_config
        self._engine = None  # 延迟创建引擎
        self._initialized = True

    def set_config(self, db_config: DatabaseConfig) -> None:
        """更新数据库配置

        在应用启动时调用，确保使用正确的配置。
        配置更新后，下次访问引擎时会使用新配置创建引擎。

        Args:
            db_config: 新的数据库配置

        示例:
            >>> db = DatabaseManager()
            >>> db.set_config(DatabaseConfig(db_name="myapp.db"))
        """
        self.db_config = db_config
        self._engine = None  # 重置引擎，下次访问时重新创建

    @property
    def engine(self):
        """获取数据库引擎（延迟创建）

        首次访问时创建引擎，确保配置已经设置。

        Returns:
            SQLAlchemy Engine 实例
        """
        if self._engine is None:
            self._engine = create_engine(
                self.db_config.database_url,
                echo=False,
                connect_args={"check_same_thread": False},
                pool_size=5,
                max_overflow=10,
            )
            # 启用外键约束
            @event.listens_for(self._engine, "connect")
            def enable_foreign_keys(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")
                cursor.close()
        return self._engine

    def get_session(self):
        """获取数据库会话上下文管理器

        Returns:
            会话上下文管理器，支持 with 语句

        示例:
            >>> db = DatabaseManager()
            >>> with db.get_session() as session:
            ...     # 在此会话中执行数据库操作
            ...     user = user_crud.get(session, 1)
        """
        return Session(self.engine)

    def init_database(self) -> None:
        """初始化数据库

        创建所有数据库表，通常在应用启动时调用一次。

        示例:
            >>> db = DatabaseManager()
            >>> db.init_database()
        """
        initializer = DatabaseInitializer(self.db_config)
        initializer.init_database()

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例

        主要用于测试场景，重置后下次创建将生成新实例。

        示例:
            >>> DatabaseManager.reset_instance()
        """
        cls._instance = None


__all__ = [
    "DatabaseInitializer",
    "init_database",
    "DatabaseManager",
]
