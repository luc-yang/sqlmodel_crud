"""SQLModel CRUD 模块"""

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
    CreateInputType,
    UpdateInputType,
    FilterDict,
)


from .scanner import ModelScanner, ModelMeta, FieldMeta, FieldType
from .generator import CodeGenerator, GeneratedFile, generate
from .detector import ChangeDetector, ModelChange
from .config import (
    GeneratorConfig,
    load_config,
    load_config_from_file,
    load_config_from_pyproject,
)
from .path_resolver import PathResolver

__version__ = "1.1.1"
__author__ = "LucYang 杨艺斌"

__all__ = [
    "CRUDBase",
    "AsyncCRUDBase",
    "SoftDeleteMixin",
    "RestoreMixin",
    "AsyncRestoreMixin",
    "DatabaseManager",
    "ErrorCode",
    "CRUDError",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    "DuplicateError",
    "ModelType",
    "CreateInputType",
    "UpdateInputType",
    "FilterDict",
    "ModelScanner",
    "ModelMeta",
    "FieldMeta",
    "FieldType",
    "CodeGenerator",
    "GeneratedFile",
    "generate",
    "ChangeDetector",
    "ModelChange",
    "GeneratorConfig",
    "load_config",
    "load_config_from_file",
    "load_config_from_pyproject",
    "PathResolver",
]
