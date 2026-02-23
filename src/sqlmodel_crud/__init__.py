"""
SQLModel CRUD 模块

基于 SQLModel 的可复用 CRUD 模块，提供通用的数据库操作基类。

主要功能：
    - CRUDBase: 通用 CRUD 操作基类
    - DatabaseManager: 数据库连接管理器
    - 异常类: 统一的错误处理机制
    - 代码生成器: 自动生成 CRUD 代码

快速开始：
    >>> from sqlmodel import SQLModel, Field
    >>> from sqlmodel_crud import CRUDBase, DatabaseManager
    >>>
    >>> # 定义模型
    >>> class User(SQLModel, table=True):
    ...     id: int = Field(default=None, primary_key=True)
    ...     name: str
    ...     email: str
    >>>
    >>> # 创建 CRUD 类
    >>> class UserCRUD(CRUDBase[User, User, User]):
    ...     def __init__(self):
    ...         super().__init__(User)
    >>>
    >>> # 使用
    >>> db = DatabaseManager("sqlite:///example.db")
    >>> db.create_tables()
    >>>
    >>> with db.get_session() as session:
    ...     user_crud = UserCRUD()
    ...     user = user_crud.create(session, {"name": "张三", "email": "zhang@example.com"})

代码生成器：
    >>> from sqlmodel_crud import ModelScanner, CodeGenerator, GeneratorConfig
    >>>
    >>> # 扫描模型
    >>> scanner = ModelScanner()
    >>> models = scanner.scan_module("app.models")
    >>>
    >>> # 生成代码
    >>> config = GeneratorConfig(output_dir="app/generated")
    >>> generator = CodeGenerator(config)
    >>> files = generator.generate(models)
    >>> generator.write_files(files)
"""

from .base import (
    CRUDBase,
    AsyncCRUDBase,
    SoftDeleteMixin,
    RestoreMixin,
    AsyncRestoreMixin,
)
from .database import DatabaseManager
from .exceptions import (
    ErrorCode,
    CRUDError,
    ValidationError,
    NotFoundError,
    DatabaseError,
    DuplicateError,
)
from .types import (
    ModelType,
    CreateSchemaType,
    UpdateSchemaType,
    FilterDict,
)

# 代码生成器相关导入
from .scanner import ModelScanner, ModelMeta, FieldMeta, FieldType
from .generator import CodeGenerator, GeneratedFile, generate
from .detector import ChangeDetector, ModelChange
from .config import (
    GeneratorConfig,
    DEFAULT_CONFIG,
    load_config,
    load_config_from_file,
    load_config_from_pyproject,
    VALID_GENERATORS,
)

__version__ = "1.0.0"
__author__ = "LucYang 杨艺斌"

__all__ = [
    # 核心类
    "CRUDBase",
    "AsyncCRUDBase",
    "SoftDeleteMixin",
    "RestoreMixin",
    "AsyncRestoreMixin",
    "DatabaseManager",
    # 异常类
    "ErrorCode",
    "CRUDError",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    "DuplicateError",
    # 类型
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType",
    "FilterDict",
    # 代码生成器 - 扫描器
    "ModelScanner",
    "ModelMeta",
    "FieldMeta",
    "FieldType",
    # 代码生成器 - 生成器
    "CodeGenerator",
    "GeneratedFile",
    "generate",
    # 代码生成器 - 变更检测
    "ChangeDetector",
    "ModelChange",
    # 代码生成器 - 配置
    "GeneratorConfig",
    "DEFAULT_CONFIG",
    "load_config",
    "load_config_from_file",
    "load_config_from_pyproject",
    "VALID_GENERATORS",
]
