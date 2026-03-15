"""模型扫描器模块。"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type, Union, get_origin, get_args
from enum import Enum
import inspect
import importlib
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
    """字段元数据类。"""

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
        """判断字段是否为必填项。"""
        return (
            not self.nullable and self.default is None and self.default_factory is None
        )

    def is_auto_increment(self) -> bool:
        """判断字段是否为自增主键。"""
        return self.primary_key and self.default is None

    def to_dict(self) -> Dict[str, Any]:
        """将字段元数据转换为字典。"""
        data = asdict(self)

        data["field_type"] = self.field_type.value

        data["python_type"] = self._type_to_string(self.python_type)
        return data

    @staticmethod
    def _type_to_string(python_type: Type[Any]) -> str:
        """将 Python 类型转换为字符串表示。"""
        if hasattr(python_type, "__name__"):
            return python_type.__name__
        return str(python_type)


@dataclass
class ModelMeta:
    """模型元数据类。"""

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
        """根据名称获取字段元数据。"""
        for field_meta in self.fields:
            if field_meta.name == name:
                return field_meta
        return None

    def get_required_fields(self) -> List[FieldMeta]:
        """获取所有必填字段。"""
        return [f for f in self.fields if f.is_required()]

    def get_optional_fields(self) -> List[FieldMeta]:
        """获取所有可选字段。"""
        return [f for f in self.fields if not f.is_required()]

    def get_relationship_fields(self) -> List[FieldMeta]:
        """获取所有关系字段。"""
        return [f for f in self.fields if f.field_type == FieldType.RELATIONSHIP]

    def get_primary_key_fields(self) -> List[FieldMeta]:
        """获取所有主键字段。"""
        return [f for f in self.fields if f.primary_key]

    def to_dict(self) -> Dict[str, Any]:
        """将模型元数据转换为字典。"""
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
    """模型扫描器类。"""

    def __init__(self, config: Optional[Any] = None):
        """初始化模型扫描器。"""
        self.config = config
        self.scanned_models: Dict[str, ModelMeta] = {}

    def scan_model(self, model_class: Type[SQLModel]) -> ModelMeta:
        """扫描单个模型类。"""

        if not isinstance(model_class, type) or not issubclass(model_class, SQLModel):
            raise ValueError(f"{model_class} 不是有效的 SQLModel 类")

        cache_key = f"{model_class.__module__}.{model_class.__name__}"
        if cache_key in self.scanned_models:
            return self.scanned_models[cache_key]

        model_meta = ModelMeta(
            name=model_class.__name__,
            module=model_class.__module__,
            description=model_class.__doc__,
        )

        model_meta.is_table = hasattr(model_class, "__tablename__")
        if model_meta.is_table:
            model_meta.table_name = getattr(model_class, "__tablename__", None)

        fields_info = model_class.model_fields

        for field_name in fields_info:
            field_meta = self._extract_field_info(model_class, field_name)
            model_meta.fields.append(field_meta)

            if field_meta.primary_key:
                model_meta.primary_keys.append(field_name)

            if field_meta.foreign_key:
                model_meta.foreign_keys[field_name] = field_meta.foreign_key

        if model_meta.is_table and hasattr(model_class, "__table__"):
            table = model_class.__table__

            for idx in table.indexes:
                index_info = {
                    "name": idx.name,
                    "columns": [col.name for col in idx.columns],
                    "unique": idx.unique,
                }

                where_clause = None
                if hasattr(idx, "dialect_kwargs"):
                    kwargs = dict(idx.dialect_kwargs)

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

            for constraint in table.constraints:
                if hasattr(constraint, "columns"):
                    col_names = [col.name for col in constraint.columns]
                    if col_names and col_names not in model_meta.unique_constraints:
                        model_meta.unique_constraints.append(col_names)

        self.scanned_models[cache_key] = model_meta

        return model_meta

    def scan(self, target: str) -> List[ModelMeta]:
        """扫描模块、目录或单文件。"""
        target_path = Path(target).expanduser()

        if target_path.exists():
            if target_path.is_dir():
                return self._scan_directory(str(target_path))
            if target_path.is_file():
                if target_path.suffix != ".py":
                    raise ValueError(f"路径必须是 Python 文件或目录: {target}")
                return self._scan_file(target_path)
            raise ValueError(f"路径必须是文件或目录: {target}")

        try:
            module = importlib.import_module(target)
        except Exception as exc:
            raise ValueError(f"无法找到模块或路径: {target}") from exc

        return self._scan_imported_module(module)

    def _scan_directory(self, directory_path: str) -> List[ModelMeta]:
        """扫描目录中的所有 SQLModel 类。"""
        path = Path(directory_path).resolve()

        if not path.exists():
            raise ValueError(f"目录不存在: {directory_path}")

        if not path.is_dir():
            raise ValueError(f"路径必须是目录: {directory_path}")

        init_file = path / "__init__.py"
        models = []
        if init_file.exists():
            try:
                package_models = self._scan_as_package(path)
                if package_models:
                    return package_models
            except ImportError:
                pass

        self._scan_directory_files(path, models)

        return models

    def _scan_as_package(self, path: Path) -> List[ModelMeta]:
        """将目录作为 Python 包扫描。"""

        package_root = self._find_package_root(path)
        if not package_root:
            raise ImportError(f"无法确定包根目录: {path}")

        module_name = self._calculate_module_name(path, package_root)
        if not module_name:
            raise ImportError(f"无法计算模块名: {path}")

        root_dir = str(package_root)
        added_to_path = False
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            added_to_path = True

        try:

            module = __import__(module_name, fromlist=["*"])
            return self._scan_imported_module(module)
        finally:

            if added_to_path and root_dir in sys.path:
                sys.path.remove(root_dir)

    def _find_package_root(self, path: Path) -> Optional[Path]:
        """查找包根目录。"""
        current = path
        root = current

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
        """计算模块名。"""
        try:
            rel_path = path.relative_to(root)
            parts = list(rel_path.parts)
            return ".".join(parts) if parts else None
        except ValueError:
            return None

    def _scan_directory_files(self, path: Path, models: List[ModelMeta]) -> None:
        """逐个扫描目录中的 Python 文件。"""

        exclude_dirs = self._get_exclude_dirs()

        for py_file in path.rglob("*.py"):

            if py_file.name.startswith("_"):
                continue

            if self._is_in_excluded_dir(py_file, exclude_dirs):
                continue

            try:
                file_models = self._scan_file(py_file)
                models.extend(file_models)
            except ValidationError:

                continue

    def _get_exclude_dirs(self) -> List[str]:
        """获取需要排除的目录名称列表。"""

        default_excludes = {
            "generated",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
        }

        if self.config and hasattr(self.config, "output_dir"):
            output_dir = Path(self.config.output_dir).name
            default_excludes.add(output_dir)

        return list(default_excludes)

    def _is_in_excluded_dir(self, file_path: Path, exclude_dirs: List[str]) -> bool:
        """检查文件是否在排除目录中。"""
        for part in file_path.parts:
            if part in exclude_dirs:
                return True
        return False

    def _scan_file(self, file_path: Path) -> List[ModelMeta]:
        """扫描单个 Python 文件中的 SQLModel 类。"""
        models = []

        file_path = file_path.resolve()

        parts = file_path.parts
        package_root = None
        package_parts = []

        for i in range(len(parts) - 1, 0, -1):
            test_path = Path(*parts[:i])
            if (test_path / "__init__.py").exists():
                package_parts.insert(0, parts[i - 1])
            else:
                if package_parts:
                    package_root = test_path
                break

        if package_root and package_parts:

            rel_parts = file_path.relative_to(package_root).parts
            module_name = ".".join(
                package_parts[:-1] + list(rel_parts[:-1]) + [file_path.stem]
            )
            package_name = ".".join(package_parts[:-1] + list(rel_parts[:-1]))
        else:
            module_name = file_path.stem
            package_name = None

        added_to_path = False
        if package_root and str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))
            added_to_path = True

        try:

            spec = importlib.util.spec_from_file_location(
                module_name, file_path, submodule_search_locations=None
            )
            if spec is None or spec.loader is None:
                return models

            module = importlib.util.module_from_spec(spec)

            if package_name:
                module.__package__ = package_name

            sys.modules[module_name] = module

            spec.loader.exec_module(module)

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

            if added_to_path and package_root and str(package_root) in sys.path:
                sys.path.remove(str(package_root))

        return models

    def _scan_imported_module(self, module: Any) -> List[ModelMeta]:
        """扫描模块对象中的所有 SQLModel 类。"""
        models = []

        exclude_models = []
        if self.config and hasattr(self.config, "exclude_models"):
            exclude_models = self.config.exclude_models

        for name, obj in inspect.getmembers(module):

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

                    raise ValidationError(
                        f"扫描模型失败: {e}", context={"model": name}
                    ) from e

        return models

    def _extract_field_info(
        self, model_class: Type[SQLModel], field_name: str
    ) -> FieldMeta:
        """从模型类中提取字段信息。"""
        field_meta = FieldMeta(name=field_name)

        field_info = None
        if field_name in model_class.model_fields:
            field_info = model_class.model_fields[field_name]

        if (
            hasattr(model_class, "__annotations__")
            and field_name in model_class.__annotations__
        ):
            field_meta.python_type = model_class.__annotations__[field_name]
            field_meta.field_type = self._determine_field_type(field_meta.python_type)

        if field_info is not None:

            if hasattr(field_info, "default"):
                default = field_info.default
                if default is not None and default is not ...:
                    field_meta.default = default

            if (
                hasattr(field_info, "default_factory")
                and field_info.default_factory is not None
            ):
                field_meta.default_factory = field_info.default_factory

            if hasattr(field_info, "description"):
                field_meta.description = field_info.description

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

            if hasattr(field_info, "foreign_key"):
                fk_value = field_info.foreign_key

                if fk_value is not None and not str(fk_value).startswith(
                    "PydanticUndefined"
                ):
                    field_meta.foreign_key = fk_value

            if hasattr(field_info, "primary_key"):
                field_meta.primary_key = field_info.primary_key

            if hasattr(field_info, "unique"):
                field_meta.unique = field_info.unique

            if hasattr(field_info, "index"):
                field_meta.index = field_info.index

            if hasattr(field_info, "nullable"):
                field_meta.nullable = field_info.nullable
            else:

                origin = get_origin(field_meta.python_type)
                args = get_args(field_meta.python_type)
                field_meta.nullable = origin is Union and type(None) in args

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

            if column.foreign_keys:
                fk = list(column.foreign_keys)[0]
                try:
                    field_meta.foreign_key = f"{fk.column.table.name}.{fk.column.name}"
                except NoReferencedTableError:

                    pass

            if hasattr(column.type, "length"):
                field_meta.max_length = column.type.length

        if hasattr(model_class, "__mapper__") and model_class.__mapper__ is not None:
            try:
                mapper: Mapper = model_class.__mapper__

                relationships = mapper.relationships
                if field_name in relationships:
                    rel = relationships[field_name]
                    field_meta.field_type = FieldType.RELATIONSHIP
                    field_meta.relationship_model = rel.mapper.class_.__name__

                    if rel.secondary is not None:

                        field_meta.relationship_type = "many-to-many"
                    elif rel.uselist:
                        field_meta.relationship_type = "one-to-many"
                    else:
                        field_meta.relationship_type = "one-to-one"
            except Exception as e:

                if field_meta.field_type == FieldType.RELATIONSHIP:

                    pass
                else:

                    try:
                        python_type = field_meta.python_type

                        origin = get_origin(python_type)
                        args = get_args(python_type)

                        if origin is list and args:

                            field_meta.field_type = FieldType.RELATIONSHIP
                            field_meta.relationship_type = "one-to-many"
                            rel_type = args[0]
                            if hasattr(rel_type, "__name__"):
                                field_meta.relationship_model = rel_type.__name__
                        elif origin is Union and type(None) in args:

                            for arg in args:
                                if arg is not type(None) and hasattr(arg, "__name__"):
                                    field_meta.field_type = FieldType.RELATIONSHIP
                                    field_meta.relationship_type = "one-to-one"
                                    field_meta.relationship_model = arg.__name__
                                    break
                    except Exception:

                        pass

        return field_meta

    def _determine_field_type(self, python_type: Type[Any]) -> FieldType:
        """根据 Python 类型确定字段类型。"""

        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Union and len(args) == 2 and type(None) in args:

            python_type = args[0] if args[1] is type(None) else args[1]
            origin = get_origin(python_type)
            args = get_args(python_type)

        if origin is list:
            return FieldType.LIST

        if origin is dict:
            return FieldType.JSON

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

        for py_type, field_type in type_mapping.items():
            if python_type is py_type or (
                isinstance(python_type, type) and issubclass(python_type, py_type)
            ):
                return field_type

        if isinstance(python_type, type) and issubclass(python_type, Enum):
            return FieldType.ENUM

        return FieldType.UNKNOWN

    def get_cached_model(
        self, name: str, module: Optional[str] = None
    ) -> Optional[ModelMeta]:
        """从缓存中获取已扫描的模型。"""
        if module:

            cache_key = f"{module}.{name}"
            return self.scanned_models.get(cache_key)

        if name in self.scanned_models:
            return self.scanned_models[name]

        for key, model in self.scanned_models.items():
            if key.endswith(f".{name}"):
                return model

        return None

    def clear_cache(self) -> None:
        """清空扫描缓存。"""
        self.scanned_models.clear()

    def get_all_cached_models(self) -> List[ModelMeta]:
        """获取所有已缓存的模型。"""
        return list(self.scanned_models.values())
