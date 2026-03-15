"""代码生成配置。"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GeneratorConfig(BaseModel):
    """代码生成配置。"""

    model_config = ConfigDict(extra="forbid")

    models_path: str = Field(
        default="app/models",
        description="模型扫描路径（文件、目录或模块路径）",
    )
    output_dir: str = Field(default="app/generated", description="代码输出目录")
    template_dir: Optional[str] = Field(default=None, description="自定义模板目录")
    crud_suffix: str = Field(default="CRUD", description="CRUD 类后缀")
    use_async: bool = Field(default=False, description="是否生成异步代码")
    include_docstrings: bool = Field(default=True, description="是否包含文档字符串")
    pagination_default_size: int = Field(default=100, description="分页默认大小")
    pagination_max_size: int = Field(default=1000, description="分页最大大小")
    type_mapping: Dict[str, str] = Field(default_factory=dict, description="类型映射")
    exclude_models: List[str] = Field(default_factory=list, description="排除模型列表")
    snapshot_file: str = Field(
        default=".sqlmodel-crud-snapshot.json",
        description="快照文件路径",
    )
    generate_data_layer: bool = Field(
        default=True,
        description="是否生成数据层基础设施文件",
    )
    data_layer_db_name: str = Field(default="app.db", description="数据库文件名")
    enable_foreign_keys: bool = Field(default=True, description="是否启用外键约束")
    echo_sql: bool = Field(default=False, description="是否输出 SQL")
    pool_size: int = Field(default=5, description="连接池大小")
    max_overflow: int = Field(default=10, description="最大溢出连接数")
    generate_model_copy: bool = Field(default=True, description="是否复制模型文件")
    soft_delete_field: str = Field(default="is_deleted", description="软删除字段名")
    soft_delete_default: bool = Field(default=False, description="软删除字段默认值")
    timestamp_fields: List[str] = Field(
        default_factory=lambda: ["created_at", "updated_at"],
        description="自动时间戳字段名",
    )
    format_code: bool = Field(default=False, description="是否自动格式化")
    line_length: int = Field(default=88, description="代码行长度限制")
    include_type_hints: bool = Field(default=True, description="是否包含完整类型注解")
    backup_before_generate: bool = Field(
        default=False, description="是否先备份现有文件"
    )
    backup_suffix: str = Field(default=".bak", description="备份文件后缀")

    @field_validator("models_path", "output_dir")
    @classmethod
    def _validate_non_empty_path(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("路径不能为空")
        return value.strip()

    @field_validator("template_dir")
    @classmethod
    def _validate_template_dir_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("模板目录不能为空字符串")
        return value.strip()

    @model_validator(mode="after")
    def validate_path_conflict(self) -> "GeneratorConfig":
        models_path = Path(self.models_path).resolve(strict=False)
        output_dir = Path(self.output_dir).resolve(strict=False)

        try:
            models_path.relative_to(output_dir)
        except ValueError:
            return self

        if self.generate_model_copy:
            self.generate_model_copy = False
        return self

    def validate_all(self) -> "GeneratorConfig":
        self._validate_models_path_runtime()
        self._validate_output_dir_runtime()
        self._validate_template_dir_runtime()
        return self

    def _validate_models_path_runtime(self) -> None:
        models_path = Path(self.models_path)
        if models_path.exists():
            if not models_path.is_dir() and not models_path.is_file():
                raise ValueError(f"模型路径必须是文件或目录: {self.models_path}")
            return

        if _looks_like_module_path(self.models_path):
            try:
                importlib.import_module(self.models_path)
            except Exception as exc:
                raise ValueError(
                    f"模型路径不存在且模块导入失败: {self.models_path}"
                ) from exc
            return

        raise ValueError(f"模型路径不存在: {self.models_path}")

    def _validate_output_dir_runtime(self) -> None:
        output_path = Path(self.output_dir)
        if output_path.exists() and not output_path.is_dir():
            raise ValueError(f"输出路径必须是目录: {self.output_dir}")
        output_path.mkdir(parents=True, exist_ok=True)

    def _validate_template_dir_runtime(self) -> None:
        if self.template_dir is None:
            return

        template_path = Path(self.template_dir)
        if not template_path.exists():
            raise ValueError(f"模板目录不存在: {self.template_dir}")
        if not template_path.is_dir():
            raise ValueError(f"模板路径必须是目录: {self.template_dir}")


def _default_config_data() -> Dict[str, Any]:
    return GeneratorConfig().model_dump()


def _load_toml_file(path: str) -> Optional[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return None

    import tomllib

    try:
        with open(file_path, "rb") as handle:
            return tomllib.load(handle)
    except Exception as exc:
        raise ValueError(f"解析配置文件失败: {path}: {exc}") from exc


def _extract_config_data(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    config_data = data.get("tool", {}).get("sqlmodel-crud", {})
    if not config_data:
        config_data = data.get("sqlmodel-crud", {})
    if not config_data:
        config_data = {
            key: value
            for key, value in data.items()
            if key in GeneratorConfig.model_fields
        }
    return config_data or None


def _get_config_from_dict(
    data: Dict[str, Any],
    *,
    source: str = "配置",
) -> Optional[GeneratorConfig]:
    config_data = _extract_config_data(data)
    if not config_data:
        return None

    try:
        return GeneratorConfig(**config_data)
    except Exception as exc:
        raise ValueError(f"{source}无效: {exc}") from exc


def load_config_from_pyproject() -> Optional[GeneratorConfig]:
    """从最近的 pyproject.toml 读取配置。"""

    current_dir = Path.cwd()
    for parent in [current_dir, *current_dir.parents]:
        pyproject_path = parent / "pyproject.toml"
        if not pyproject_path.exists():
            continue

        data = _load_toml_file(str(pyproject_path))
        if data is None:
            continue

        return _get_config_from_dict(data, source=f"pyproject.toml({pyproject_path})")

    return None


def load_config_from_file(path: str) -> Optional[GeneratorConfig]:
    """从指定文件读取配置。"""

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    data = _load_toml_file(path)
    if data is None:
        return None

    return _get_config_from_dict(data, source=f"配置文件({path})")


def _load_from_env() -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    prefix = "SQLMODEL_CRUD_"

    mappings = {
        "MODELS_PATH": "models_path",
        "OUTPUT_DIR": "output_dir",
        "TEMPLATE_DIR": "template_dir",
        "CRUD_SUFFIX": "crud_suffix",
        "EXCLUDE_MODELS": "exclude_models",
        "SNAPSHOT_FILE": "snapshot_file",
        "GENERATE_DATA_LAYER": "generate_data_layer",
        "DATA_LAYER_DB_NAME": "data_layer_db_name",
        "ENABLE_FOREIGN_KEYS": "enable_foreign_keys",
        "ECHO_SQL": "echo_sql",
        "POOL_SIZE": "pool_size",
        "MAX_OVERFLOW": "max_overflow",
        "GENERATE_MODEL_COPY": "generate_model_copy",
        "SOFT_DELETE_FIELD": "soft_delete_field",
        "SOFT_DELETE_DEFAULT": "soft_delete_default",
        "FORMAT_CODE": "format_code",
        "LINE_LENGTH": "line_length",
        "INCLUDE_TYPE_HINTS": "include_type_hints",
        "BACKUP_BEFORE_GENERATE": "backup_before_generate",
        "BACKUP_SUFFIX": "backup_suffix",
    }

    bool_fields = {
        "enable_foreign_keys",
        "echo_sql",
        "generate_model_copy",
        "soft_delete_default",
        "format_code",
        "include_type_hints",
        "backup_before_generate",
        "generate_data_layer",
    }
    int_fields = {"pool_size", "max_overflow", "line_length"}
    list_fields = {"exclude_models"}

    for env_key, config_key in mappings.items():
        env_value = os.getenv(f"{prefix}{env_key}")
        if env_value is None:
            continue

        if config_key in bool_fields:
            config[config_key] = env_value.lower() in {"true", "1", "yes", "on"}
        elif config_key in int_fields:
            try:
                config[config_key] = int(env_value)
            except ValueError:
                continue
        elif config_key in list_fields:
            config[config_key] = [
                item.strip() for item in env_value.split(",") if item.strip()
            ]
        else:
            config[config_key] = env_value

    return config


def load_config(config_path: Optional[str] = None) -> GeneratorConfig:
    """按文件配置、环境变量顺序加载配置。"""

    config_dict = _default_config_data()

    if config_path:
        file_config = load_config_from_file(config_path)
    else:
        file_config = load_config_from_pyproject()
        if file_config is None:
            standalone_path = Path(".sqlmodel-crud.toml")
            if standalone_path.exists():
                file_config = load_config_from_file(str(standalone_path))

    if file_config is not None:
        config_dict.update(file_config.model_dump(exclude_unset=True))

    config_dict.update(_load_from_env())
    return GeneratorConfig(**config_dict)


def _looks_like_module_path(value: str) -> bool:
    if "/" in value or "\\" in value:
        return False

    parts = [part for part in value.split(".") if part]
    if len(parts) < 2:
        return False

    return all(part.isidentifier() for part in parts)
