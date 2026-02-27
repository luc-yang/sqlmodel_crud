# coding:utf-8
"""
数据库配置模块

提供数据库路径管理和连接URL生成功能。
该文件由 SQLModel CRUD 生成器自动生成。

生成时间: 2026-02-27 13:46:00
警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""

import os
from pathlib import Path
from typing import Optional


class DatabaseConfig:
    """数据库配置类

    管理数据库文件路径和连接URL的生成。

    Attributes:
        db_name: 数据库文件名
        db_dir: 数据库目录路径
        db_path: 数据库完整路径
        database_url: 数据库连接URL

    示例:
        >>> config = DatabaseConfig()
        >>> print(config.database_url)
        'sqlite:///path/to/database.db'
    """

    def __init__(
        self,
        db_name: Optional[str] = None,
        db_dir: Optional[str] = None,
    ):
        """初始化数据库配置

        Args:
            db_name: 数据库文件名，默认为 app.db
            db_dir: 数据库目录路径，默认为 AppData 目录
        """
        self._db_name = db_name if db_name is not None and db_name != "" else "app.db"
        self._db_dir = db_dir if db_dir is not None and db_dir != "" else "AppData"

    @property
    def db_dir(self) -> Path:
        """获取数据库目录路径

        如果未指定目录，则返回 AppData 目录。

        Returns:
            数据库目录的 Path 对象
        """
        if self._db_dir:
            return Path(self._db_dir)

        # 默认使用 AppData 目录
        app_dir = Path(__file__).parent.parent.parent
        db_dir = app_dir / "AppData"

        # 确保目录存在
        db_dir.mkdir(parents=True, exist_ok=True)

        return db_dir

    @property
    def db_name(self) -> str:
        """获取数据库文件名

        Returns:
            数据库文件名字符串
        """
        return self._db_name

    @property
    def db_path(self) -> Path:
        """获取数据库完整路径

        Returns:
            数据库文件的完整 Path 对象
        """
        return self.db_dir / self.db_name

    @property
    def database_url(self) -> str:
        """获取数据库连接URL

        生成 SQLite 数据库连接URL。

        Returns:
            数据库连接URL字符串

        示例:
            >>> config = DatabaseConfig()
            >>> url = config.database_url
            >>> print(url)
            'sqlite:///C:/Users/.../AppData/app.db'
        """
        # SQLite 需要使用绝对路径或 file:// 格式
        abs_path = self.db_path.resolve()
        return f"sqlite:///{abs_path}"

    def exists(self) -> bool:
        """检查数据库文件是否存在

        Returns:
            如果数据库文件存在返回 True，否则返回 False
        """
        return self.db_path.is_file()

    def ensure_directory(self) -> Path:
        """确保数据库目录存在

        如果目录不存在则创建。

        Returns:
            数据库目录的 Path 对象
        """
        self.db_dir.mkdir(parents=True, exist_ok=True)
        return self.db_dir


# 默认数据库配置实例
default_config = DatabaseConfig()


__all__ = ["DatabaseConfig", "default_config"]
