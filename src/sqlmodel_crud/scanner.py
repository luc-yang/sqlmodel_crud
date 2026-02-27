"""
模型扫描器模块。

该模块提供了扫描 SQLModel 模型并提取元数据的功能，
用于后续代码生成。
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type, Union, get_origin, get_args
from enum import Enum
import inspect
import importlib.util
import sys
from pathlib import Path
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

from sqlmodel import SQLModel
from sqlalchemy import Column
from sqlalchemy.orm import Mapper
from sqlalchemy.exc import NoReferencedTableError

from .exceptions import ValidationError


class FieldType(Enum):
    """字段类型枚举。"""

    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    DECIMAL = "Decimal"
    JSON = "dict"
    LIST = "list"
    UUID = "UUID"
    BYTES = "bytes"
    ENUM = "Enum"
    RELATIONSHIP = "relationship"
    UNKNOWN = "unknown"


@dataclass
class FieldMeta:
    """
    字段元数据类。

    存储 SQLModel 字段的详细信息，包括名称、类型、约束等。

    Attributes:
        name: 字段名称
        field_type: 字段类型
        python_type: Python 类型注解
        nullable: 是否可为空
        primary_key: 是否为主键
        default: 默认值
        default_factory: 默认值工厂函数
        foreign_key: 外键引用
        unique: 是否唯一
        index: 是否索引
        description: 字段描述
        max_length: 最大长度（用于字符串）
        ge: 大于等于（用于数值）
        le: 小于等于（用于数值）
        gt: 大于（用于数值）
        lt: 小于（用于数值）
        regex: 正则表达式（用于字符串验证）
        relationship_model: 关联模型名称（用于关系字段）
        relationship_type: 关系类型（one-to-one, one-to-many, many-to-many）
    """

    name: str
    field_type: FieldType = FieldType.UNKNOWN
    python_type: Type[Any] = Any
    nullable: bool = True
    primary_key: bool = False
    default: Any = None
    default_factory: Optional[Any] = None
    foreign_key: Optional[str] = None
    unique: bool = False
    index: bool = False
    description: Optional[str] = None
    max_length: Optional[int] = None
    ge: Optional[Union[int, float]] = None
    le: Optional[Union[int, float]] = None
    gt: Optional[Union[int, float]] = None
    lt: Optional[Union[int, float]] = None
    regex: Optional[str] = None
    relationship_model: Optional[str] = None
    relationship_type: Optional[str] = None

    def is_required(self) -> bool:
        """
        判断字段是否为必填项。

        Returns:
            如果字段不可为空且没有默认值，返回 True
        """
        return (
            not self.nullable and self.default is None and self.default_factory is None
        )

    def is_auto_increment(self) -> bool:
        """
        判断字段是否为自增主键。

        Returns:
            如果字段是主键且没有默认值，返回 True
        """
        return self.primary_key and self.default is None

    def to_dict(self) -> Dict[str, Any]:
        """
        将字段元数据转换为字典。

        Returns:
            字段元数据字典
        """
        data = asdict(self)
        # 将 FieldType 枚举转换为字符串
        data["field_type"] = self.field_type.value
        # 将 Python 类型转换为字符串表示
        data["python_type"] = self._type_to_string(self.python_type)
        return data

    @staticmethod
    def _type_to_string(python_type: Type[Any]) -> str:
        """
        将 Python 类型转换为字符串表示。

        Args:
            python_type: Python 类型

        Returns:
            类型字符串表示
        """
        if hasattr(python_type, "__name__"):
            return python_type.__name__
        return str(python_type)


@dataclass
class ModelMeta:
    """
    模型元数据类。

    存储 SQLModel 的完整元数据信息，包括表名、字段、关系等。

    Attributes:
        name: 模型类名
        table_name: 数据库表名
        module: 模型所在模块名
        fields: 字段元数据列表
        primary_keys: 主键字段名列表
        foreign_keys: 外键字段信息
        indexes: 索引信息
        unique_constraints: 唯一约束信息
        description: 模型描述
        is_table: 是否为数据库表（而非仅 Pydantic 模型）
    """

    name: str
    table_name: Optional[str] = None
    module: Optional[str] = None
    fields: List[FieldMeta] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: Dict[str, str] = field(default_factory=dict)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    unique_constraints: List[List[str]] = field(default_factory=list)
    description: Optional[str] = None
    is_table: bool = False

    def get_field(self, name: str) -> Optional[FieldMeta]:
        """
        根据名称获取字段元数据。

        Args:
            name: 字段名称

        Returns:
            字段元数据，如果不存在返回 None
        """
        for field_meta in self.fields:
            if field_meta.name == name:
                return field_meta
        return None

    def get_required_fields(self) -> List[FieldMeta]:
        """
        获取所有必填字段。

        Returns:
            必填字段列表
        """
        return [f for f in self.fields if f.is_required()]

    def get_optional_fields(self) -> List[FieldMeta]:
        """
        获取所有可选字段。

        Returns:
            可选字段列表
        """
        return [f for f in self.fields if not f.is_required()]

    def get_relationship_fields(self) -> List[FieldMeta]:
        """
        获取所有关系字段。

        Returns:
            关系字段列表
        """
        return [f for f in self.fields if f.field_type == FieldType.RELATIONSHIP]

    def get_primary_key_fields(self) -> List[FieldMeta]:
        """
        获取所有主键字段。

        Returns:
            主键字段列表
        """
        return [f for f in self.fields if f.primary_key]

    def to_dict(self) -> Dict[str, Any]:
        """
        将模型元数据转换为字典。

        Returns:
            模型元数据字典
        """
        return {
            "name": self.name,
            "table_name": self.table_name,
            "module": self.module,
            "fields": [f.to_dict() for f in self.fields],
            "primary_keys": self.primary_keys,
            "foreign_keys": self.foreign_keys,
            "indexes": self.indexes,
            "unique_constraints": self.unique_constraints,
            "description": self.description,
            "is_table": self.is_table,
        }


class ModelScanner:
    """
    模型扫描器类。

    用于扫描 SQLModel 模型类并提取元数据信息。

    Attributes:
        config: 生成器配置对象
        scanned_models: 已扫描的模型缓存

    Example:
        >>> scanner = ModelScanner(config)
        >>> model_meta = scanner.scan_model(User)
        >>> print(model_meta.name)
        'User'
    """

    def __init__(self, config: Optional[Any] = None):
        """
        初始化模型扫描器。

        Args:
            config: 生成器配置对象
        """
        self.config = config
        self.scanned_models: Dict[str, ModelMeta] = {}

    def scan_model(self, model_class: Type[SQLModel]) -> ModelMeta:
        """
        扫描单个模型类。

        Args:
            model_class: SQLModel 模型类

        Returns:
            模型元数据对象

        Raises:
            ValueError: 如果输入不是有效的 SQLModel 类
        """
        # 检查是否是有效的 SQLModel 类
        if not isinstance(model_class, type) or not issubclass(model_class, SQLModel):
            raise ValueError(f"{model_class} 不是有效的 SQLModel 类")

        # 检查缓存
        cache_key = f"{model_class.__module__}.{model_class.__name__}"
        if cache_key in self.scanned_models:
            return self.scanned_models[cache_key]

        # 创建模型元数据
        model_meta = ModelMeta(
            name=model_class.__name__,
            module=model_class.__module__,
            description=model_class.__doc__,
        )

        # 检查是否为数据库表
        model_meta.is_table = hasattr(model_class, "__tablename__")
        if model_meta.is_table:
            model_meta.table_name = getattr(model_class, "__tablename__", None)

        # 获取模型的字段信息
        if hasattr(model_class, "model_fields"):
            # SQLModel 0.0.14+ 使用 model_fields
            fields_info = model_class.model_fields
        elif hasattr(model_class, "__fields__"):
            # 旧版本使用 __fields__
            fields_info = model_class.__fields__
        else:
            fields_info = {}

        # 扫描每个字段
        for field_name in fields_info:
            field_meta = self._extract_field_info(model_class, field_name)
            model_meta.fields.append(field_meta)

            # 记录主键
            if field_meta.primary_key:
                model_meta.primary_keys.append(field_name)

            # 记录外键
            if field_meta.foreign_key:
                model_meta.foreign_keys[field_name] = field_meta.foreign_key

        # 获取表的索引和约束信息（如果是数据库表）
        if model_meta.is_table and hasattr(model_class, "__table__"):
            table = model_class.__table__

            # 获取索引信息
            for idx in table.indexes:
                index_info = {
                    "name": idx.name,
                    "columns": [col.name for col in idx.columns],
                    "unique": idx.unique,
                }

                # 获取部分索引（Partial Index）的 WHERE 条件
                # 支持多种数据库的部分索引
                where_clause = None
                if hasattr(idx, "dialect_kwargs"):
                    kwargs = dict(idx.dialect_kwargs)

                    # 数据库方言到 WHERE 条件参数名的映射
                    dialect_where_params = {
                        "sqlite": "sqlite_where",
                        "postgresql": "postgresql_where",
                        "mysql": "mysql_where",
                        "mssql": "mssql_where",
                        "oracle": "oracle_where",
                    }

                    for dialect, param_name in dialect_where_params.items():
                        if param_name in kwargs:
                            where_clause = str(kwargs[param_name])
                            index_info["dialect"] = dialect
                            break

                if where_clause:
                    index_info["where"] = where_clause

                model_meta.indexes.append(index_info)

            # 获取唯一约束
            for constraint in table.constraints:
                if hasattr(constraint, "columns"):
                    col_names = [col.name for col in constraint.columns]
                    if col_names and col_names not in model_meta.unique_constraints:
                        model_meta.unique_constraints.append(col_names)

        # 缓存扫描结果
        self.scanned_models[cache_key] = model_meta

        return model_meta

    def scan_directory(self, directory_path: str) -> List[ModelMeta]:
        """
        扫描目录中的所有 SQLModel 类。

        仅支持文件系统目录路径，不再支持模块导入路径。

        Args:
            directory_path: 目录路径

        Returns:
            模型元数据列表
        """
        path = Path(directory_path).resolve()

        if not path.exists():
            raise ValueError(f"目录不存在: {directory_path}")

        if not path.is_dir():
            raise ValueError(f"路径必须是目录: {directory_path}")

        models = []

        # 如果目录包含 __init__.py，尝试作为包导入
        if (path / "__init__.py").exists():
            try:
                package_models = self._scan_as_package(path)
                if package_models:
                    return package_models
            except ImportError:
                # 包导入失败，回退到逐个文件扫描
                print(f"[提示] 包导入失败，回退到逐个文件扫描: {path}")

        # 逐个文件扫描
        self._scan_directory_files(path, models)

        return models

    def _scan_as_package(self, path: Path) -> List[ModelMeta]:
        """
        将目录作为 Python 包扫描。

        Args:
            path: 包目录路径

        Returns:
            模型元数据列表

        Raises:
            ImportError: 当包导入失败时抛出
        """
        # 查找包根目录
        package_root = self._find_package_root(path)
        if not package_root:
            raise ImportError(f"无法确定包根目录: {path}")

        # 计算模块名
        module_name = self._calculate_module_name(path, package_root)
        if not module_name:
            raise ImportError(f"无法计算模块名: {path}")

        # 将包根目录添加到 sys.path
        root_dir = str(package_root)
        added_to_path = False
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            added_to_path = True

        try:
            # 导入包
            module = __import__(module_name, fromlist=["*"])
            return self._scan_module_object(module)
        finally:
            # 清理 sys.path
            if added_to_path and root_dir in sys.path:
                sys.path.remove(root_dir)

    def _find_package_root(self, path: Path) -> Optional[Path]:
        """
        查找包根目录。

        从给定路径向上查找，找到包含 __init__.py 的最顶层目录。

        Args:
            path: 起始路径

        Returns:
            包根目录，如果找不到返回 None
        """
        current = path
        root = current

        # 向上查找
        while current.parent != current:
            if (current.parent / "__init__.py").exists():
                root = current.parent
                current = current.parent
            else:
                break

        return (
            root
            if root != path
            else path.parent if (path / "__init__.py").exists() else None
        )

    def _calculate_module_name(self, path: Path, root: Path) -> Optional[str]:
        """
        计算模块名。

        Args:
            path: 目标路径
            root: 包根目录

        Returns:
            模块名，如果无法计算返回 None
        """
        try:
            rel_path = path.relative_to(root)
            parts = list(rel_path.parts)
            return ".".join(parts) if parts else None
        except ValueError:
            return None

    def _scan_directory_files(self, path: Path, models: List[ModelMeta]) -> None:
        """
        逐个扫描目录中的 Python 文件。

        Args:
            path: 目录路径
            models: 模型列表（会被修改）
        """
        # 获取需要排除的目录列表
        exclude_dirs = self._get_exclude_dirs()

        for py_file in path.rglob("*.py"):
            # 跳过以下划线开头的文件
            if py_file.name.startswith("_"):
                continue

            # 检查文件是否在排除目录中
            if self._is_in_excluded_dir(py_file, exclude_dirs):
                continue

            try:
                file_models = self._scan_file(py_file)
                models.extend(file_models)
            except ValidationError:
                # 继续扫描其他文件
                continue

    def _get_exclude_dirs(self) -> List[str]:
        """
        获取需要排除的目录名称列表。

        Returns:
            需要排除的目录名称列表
        """
        # 默认排除的目录
        default_excludes = {
            "generated",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
        }

        # 如果配置中有 output_dir，也将其加入排除列表
        if self.config and hasattr(self.config, "output_dir"):
            output_dir = Path(self.config.output_dir).name
            default_excludes.add(output_dir)

        return list(default_excludes)

    def _is_in_excluded_dir(self, file_path: Path, exclude_dirs: List[str]) -> bool:
        """
        检查文件是否在排除目录中。

        Args:
            file_path: 文件路径
            exclude_dirs: 排除的目录名称列表

        Returns:
            如果文件在排除目录中返回 True，否则返回 False
        """
        for part in file_path.parts:
            if part in exclude_dirs:
                return True
        return False

    def _scan_file(self, file_path: Path) -> List[ModelMeta]:
        """
        扫描单个 Python 文件中的 SQLModel 类。

        Args:
            file_path: Python 文件路径

        Returns:
            模型元数据列表
        """
        models = []

        # 转换为绝对路径
        file_path = file_path.resolve()

        # 查找项目根目录（包含 __init__.py 的最顶层目录）
        parts = file_path.parts
        package_root = None
        package_parts = []

        # 从文件所在目录向上查找，找到包根目录
        for i in range(len(parts) - 1, 0, -1):
            test_path = Path(*parts[:i])
            if (test_path / "__init__.py").exists():
                package_parts.insert(0, parts[i - 1])
            else:
                if package_parts:
                    package_root = test_path
                break

        # 构建模块名称
        if package_root and package_parts:
            # 计算从包根到文件的相对路径
            rel_parts = file_path.relative_to(package_root).parts
            module_name = ".".join(
                package_parts[:-1] + list(rel_parts[:-1]) + [file_path.stem]
            )
            package_name = ".".join(package_parts[:-1] + list(rel_parts[:-1]))
        else:
            module_name = file_path.stem
            package_name = None

        # 将包根目录添加到 sys.path
        added_to_path = False
        if package_root and str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))
            added_to_path = True

        try:
            # 使用 importlib 加载模块，正确处理相对导入
            spec = importlib.util.spec_from_file_location(
                module_name, file_path, submodule_search_locations=None
            )
            if spec is None or spec.loader is None:
                return models

            module = importlib.util.module_from_spec(spec)

            # 设置包名，使相对导入能够工作
            if package_name:
                module.__package__ = package_name

            # 注册模块，以便相对导入能解析
            sys.modules[module_name] = module

            # 执行模块
            spec.loader.exec_module(module)

            # 从模块中提取 SQLModel 类
            for name, obj in list(vars(module).items()):
                if name.startswith("_"):
                    continue
                try:
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, SQLModel)
                        and obj is not SQLModel
                    ):
                        model_meta = self.scan_model(obj)
                        models.append(model_meta)
                except (TypeError, AttributeError):
                    pass

        except Exception as e:
            error_msg = str(e)

            # 检测表重复定义错误
            if "is already defined for this MetaData instance" in error_msg:
                print(f"[提示] 扫描文件时检测到表重复定义: {file_path.name}")
                print(f"[提示] 可能的原因:")
                print(f"  1. 该模型已在包导入时被加载，又被逐个文件扫描重复加载")
                print(f"  2. 多个模型文件定义了同名的表")
                print(
                    f"[建议] 如果 {file_path.parent / '__init__.py'} 存在问题，可以尝试:"
                )
                print(f"  - 修复 {file_path.parent / '__init__.py'} 中的导入错误")
                print(
                    f"  - 或临时删除/重命名 {file_path.parent / '__init__.py'} 以跳过包导入"
                )

            raise ValidationError(
                f"扫描文件失败: {e}", context={"file": str(file_path)}
            ) from e
        finally:
            # 清理 sys.path
            if added_to_path and package_root and str(package_root) in sys.path:
                sys.path.remove(str(package_root))

        return models

    def _scan_module_object(self, module: Any) -> List[ModelMeta]:
        """
        扫描模块对象中的所有 SQLModel 类。

        Args:
            module: Python 模块对象

        Returns:
            模型元数据列表
        """
        models = []

        # 排除的模型名称
        exclude_models = []
        if self.config and hasattr(self.config, "exclude_models"):
            exclude_models = self.config.exclude_models

        for name, obj in inspect.getmembers(module):
            # 检查是否是 SQLModel 子类（排除 SQLModel 本身）
            if (
                isinstance(obj, type)
                and issubclass(obj, SQLModel)
                and obj is not SQLModel
                and name not in exclude_models
            ):
                try:
                    model_meta = self.scan_model(obj)
                    models.append(model_meta)
                except Exception as e:
                    # 扫描失败时抛出异常
                    raise ValidationError(
                        f"扫描模型失败: {e}", context={"model": name}
                    ) from e

        return models

    def _extract_field_info(
        self, model_class: Type[SQLModel], field_name: str
    ) -> FieldMeta:
        """
        从模型类中提取字段信息。

        Args:
            model_class: SQLModel 模型类
            field_name: 字段名称

        Returns:
            字段元数据对象
        """
        field_meta = FieldMeta(name=field_name)

        # 获取字段的 SQLModel 字段信息
        field_info = None
        if (
            hasattr(model_class, "model_fields")
            and field_name in model_class.model_fields
        ):
            field_info = model_class.model_fields[field_name]
        elif (
            hasattr(model_class, "__fields__") and field_name in model_class.__fields__
        ):
            field_info = model_class.__fields__[field_name]

        # 获取 Python 类型注解
        if (
            hasattr(model_class, "__annotations__")
            and field_name in model_class.__annotations__
        ):
            field_meta.python_type = model_class.__annotations__[field_name]
            field_meta.field_type = self._determine_field_type(field_meta.python_type)

        # 从 Field 信息中提取更多元数据
        if field_info is not None:
            # 获取默认值
            if hasattr(field_info, "default"):
                default = field_info.default
                if default is not None and default is not ...:
                    field_meta.default = default

            # 获取默认值工厂
            if (
                hasattr(field_info, "default_factory")
                and field_info.default_factory is not None
            ):
                field_meta.default_factory = field_info.default_factory

            # 获取字段描述
            if hasattr(field_info, "description"):
                field_meta.description = field_info.description

            # 获取验证约束
            if (
                hasattr(field_info, "json_schema_extra")
                and field_info.json_schema_extra
            ):
                extra = field_info.json_schema_extra
                if isinstance(extra, dict):
                    field_meta.ge = extra.get("ge")
                    field_meta.le = extra.get("le")
                    field_meta.gt = extra.get("gt")
                    field_meta.lt = extra.get("lt")
                    field_meta.regex = extra.get("pattern")
                    field_meta.max_length = extra.get("maxLength")

            # 获取外键信息
            if hasattr(field_info, "foreign_key"):
                fk_value = field_info.foreign_key
                # 只保存有效的外键值（非 None 且非 PydanticUndefined）
                if fk_value is not None and not str(fk_value).startswith(
                    "PydanticUndefined"
                ):
                    field_meta.foreign_key = fk_value

            # 获取主键信息
            if hasattr(field_info, "primary_key"):
                field_meta.primary_key = field_info.primary_key

            # 获取唯一约束
            if hasattr(field_info, "unique"):
                field_meta.unique = field_info.unique

            # 获取索引信息
            if hasattr(field_info, "index"):
                field_meta.index = field_info.index

            # 获取 nullable 信息
            if hasattr(field_info, "nullable"):
                field_meta.nullable = field_info.nullable
            else:
                # 根据类型判断
                origin = get_origin(field_meta.python_type)
                args = get_args(field_meta.python_type)
                field_meta.nullable = origin is Union and type(None) in args

        # 从 SQLAlchemy 列信息中获取更多元数据
        if (
            hasattr(model_class, "__table__")
            and model_class.__table__ is not None
            and field_name in model_class.__table__.columns
        ):
            column: Column = model_class.__table__.columns[field_name]

            field_meta.primary_key = column.primary_key
            field_meta.nullable = column.nullable
            field_meta.unique = column.unique
            field_meta.index = column.index

            # 获取外键
            if column.foreign_keys:
                fk = list(column.foreign_keys)[0]
                try:
                    field_meta.foreign_key = f"{fk.column.table.name}.{fk.column.name}"
                except NoReferencedTableError:
                    # 当外键引用的表还未在 metadata 中注册时，保留 Field 中定义的外键值
                    # 这种情况发生在跨文件引用模型时，模型是逐个文件扫描的
                    pass

            # 获取字符串长度
            if hasattr(column.type, "length"):
                field_meta.max_length = column.type.length

        # 检查是否为关系字段
        if hasattr(model_class, "__mapper__") and model_class.__mapper__ is not None:
            try:
                mapper: Mapper = model_class.__mapper__
                # 尝试访问 relationships 属性，如果引用的模型尚未加载可能会失败
                relationships = mapper.relationships
                if field_name in relationships:
                    rel = relationships[field_name]
                    field_meta.field_type = FieldType.RELATIONSHIP
                    field_meta.relationship_model = rel.mapper.class_.__name__

                    # 确定关系类型
                    if rel.secondary is not None:
                        # 多对多关系（通过关联表）
                        field_meta.relationship_type = "many-to-many"
                    elif rel.uselist:
                        field_meta.relationship_type = "one-to-many"
                    else:
                        field_meta.relationship_type = "one-to-one"
            except Exception as e:
                # 当引用的模型尚未加载时，SQLAlchemy 可能会抛出异常
                # 这种情况下，我们尝试从类型注解中推断关系信息
                if field_meta.field_type == FieldType.RELATIONSHIP:
                    # 已经通过类型注解识别为关系字段，保持已有信息
                    pass
                else:
                    # 尝试从类型注解推断关系模型名称
                    try:
                        python_type = field_meta.python_type
                        # 处理 Optional[T] 和 List[T] 类型
                        origin = get_origin(python_type)
                        args = get_args(python_type)

                        if origin is list and args:
                            # List[SomeModel] -> 一对多关系
                            field_meta.field_type = FieldType.RELATIONSHIP
                            field_meta.relationship_type = "one-to-many"
                            rel_type = args[0]
                            if hasattr(rel_type, "__name__"):
                                field_meta.relationship_model = rel_type.__name__
                        elif origin is Union and type(None) in args:
                            # Optional[SomeModel] -> 一对一关系
                            for arg in args:
                                if arg is not type(None) and hasattr(arg, "__name__"):
                                    field_meta.field_type = FieldType.RELATIONSHIP
                                    field_meta.relationship_type = "one-to-one"
                                    field_meta.relationship_model = arg.__name__
                                    break
                    except Exception:
                        # 如果推断也失败，则跳过此字段的关系信息
                        pass

        return field_meta

    def _determine_field_type(self, python_type: Type[Any]) -> FieldType:
        """
        根据 Python 类型确定字段类型。

        Args:
            python_type: Python 类型

        Returns:
            字段类型枚举值
        """
        # 处理 Optional[T] 类型
        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Union and len(args) == 2 and type(None) in args:
            # Optional[T] = Union[T, None]
            python_type = args[0] if args[1] is type(None) else args[1]
            origin = get_origin(python_type)
            args = get_args(python_type)

        # 处理 List[T] 类型
        if origin is list:
            return FieldType.LIST

        # 处理 Dict 类型
        if origin is dict:
            return FieldType.JSON

        # 映射基本类型
        type_mapping = {
            str: FieldType.STRING,
            int: FieldType.INTEGER,
            float: FieldType.FLOAT,
            bool: FieldType.BOOLEAN,
            datetime: FieldType.DATETIME,
            date: FieldType.DATE,
            time: FieldType.TIME,
            Decimal: FieldType.DECIMAL,
            UUID: FieldType.UUID,
            bytes: FieldType.BYTES,
        }

        # 检查类型或其基类
        for py_type, field_type in type_mapping.items():
            if python_type is py_type or (
                isinstance(python_type, type) and issubclass(python_type, py_type)
            ):
                return field_type

        # 检查是否为 Enum
        if isinstance(python_type, type) and issubclass(python_type, Enum):
            return FieldType.ENUM

        return FieldType.UNKNOWN

    def get_cached_model(
        self, name: str, module: Optional[str] = None
    ) -> Optional[ModelMeta]:
        """
        从缓存中获取已扫描的模型。

        Args:
            name: 模型名称
            module: 模型所在模块，如果提供则使用完整路径匹配

        Returns:
            模型元数据，如果不存在返回 None
        """
        if module:
            # 使用完整路径匹配
            cache_key = f"{module}.{name}"
            return self.scanned_models.get(cache_key)

        # 尝试直接匹配
        if name in self.scanned_models:
            return self.scanned_models[name]

        # 尝试后缀匹配（通过名称查找）
        for key, model in self.scanned_models.items():
            if key.endswith(f".{name}"):
                return model

        return None

    def clear_cache(self) -> None:
        """清空扫描缓存。"""
        self.scanned_models.clear()

    def get_all_cached_models(self) -> List[ModelMeta]:
        """
        获取所有已缓存的模型。

        Returns:
            模型元数据列表
        """
        return list(self.scanned_models.values())
