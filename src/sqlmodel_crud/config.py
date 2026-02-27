"""
SQLModel CRUD 代码生成器配置管理模块

提供配置加载、验证和管理功能，支持多种配置来源：
    - pyproject.toml 配置文件
    - .sqlmodel-crud.toml 独立配置文件
    - 环境变量
    - 默认值

配置优先级（从高到低）：
    1. 环境变量（SQLMODEL_CRUD_*）
    2. 配置文件（pyproject.toml 或 .sqlmodel-crud.toml）
    3. 默认配置

示例:
    >>> from sqlmodel_crud.config import load_config, GeneratorConfig
    >>>
    >>> # 自动加载配置
    >>> config = load_config()
    >>>
    >>> # 从指定文件加载
    >>> config = load_config_from_file("custom-config.toml")
    >>>
    >>> # 手动创建配置
    >>> config = GeneratorConfig(
    ...     models_path="app/models",
    ...     output_dir="app/generated",
    ...     generators=["crud", "schemas"]
    ... )
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# 合法的生成器类型
VALID_GENERATORS = {"crud", "schemas", "all"}


class GeneratorConfig(BaseModel):
    """SQLModel CRUD 代码生成器配置类

    使用 Pydantic BaseModel 定义配置结构，提供自动验证和序列化功能。
    支持从字典、JSON、TOML 等多种格式加载配置。

    属性:
        models_path: 模型扫描路径，用于查找 SQLModel 模型类（仅支持文件路径）
        output_dir: 代码输出目录，生成的代码文件将保存到此目录
        generators: 生成代码类型列表，可选值：crud, schemas, all
        template_dir: 自定义模板目录，用于覆盖默认模板
        crud_suffix: CRUD 类后缀，默认为 "CRUD"
        schema_suffix: Schema 类后缀，默认为 "Schema"
        type_mapping: 类型映射规则，用于自定义字段类型转换
        exclude_models: 排除的模型列表，这些模型不会被生成代码
        snapshot_file: 快照文件路径，用于增量生成

    示例:
        >>> config = GeneratorConfig(
        ...     models_path="app/models",
        ...     output_dir="app/generated",
        ...     generators=["crud", "schemas"]
        ... )
        >>> print(config.models_path)
        'app/models'
    """

    models_path: str = Field(
        default="app/models",
        description="模型扫描路径，用于查找 SQLModel 模型类（仅支持文件路径，如 app/models）",
    )
    output_dir: str = Field(
        default="app/generated",
        description="代码输出目录，生成的代码文件将保存到此目录",
    )
    generators: List[str] = Field(
        default_factory=lambda: ["crud", "schemas"],
        description="生成代码类型列表，可选值：crud, schemas, all",
    )
    template_dir: Optional[str] = Field(
        default=None,
        description="自定义模板目录，用于覆盖默认模板",
    )
    crud_suffix: str = Field(
        default="CRUD",
        description="CRUD 类后缀",
    )
    schema_suffix: str = Field(
        default="Schema",
        description="Schema 类后缀",
    )
    schema_create_suffix: str = Field(
        default="Create",
        description="Schema 创建类后缀",
    )
    schema_update_suffix: str = Field(
        default="Update",
        description="Schema 更新类后缀",
    )
    schema_response_suffix: str = Field(
        default="Response",
        description="Schema 响应类后缀",
    )
    use_async: bool = Field(
        default=True,
        description="是否生成异步代码",
    )
    include_docstrings: bool = Field(
        default=True,
        description="是否包含文档字符串",
    )
    pagination_default_size: int = Field(
        default=100,
        description="分页默认大小",
    )
    pagination_max_size: int = Field(
        default=1000,
        description="分页最大大小",
    )
    type_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="类型映射规则，用于自定义字段类型转换",
    )
    exclude_models: List[str] = Field(
        default_factory=list,
        description="排除的模型列表，这些模型不会被生成代码",
    )
    snapshot_file: str = Field(
        default=".sqlmodel-crud-snapshot.json",
        description="快照文件路径，用于增量生成",
    )
    generate_data_layer: bool = Field(
        default=True,
        description="是否生成数据层基础设施文件（config.py、database.py、__init__.py）",
    )
    data_layer_db_name: str = Field(
        default="app.db",
        description="数据层数据库文件名",
    )

    # 数据库连接配置
    enable_foreign_keys: bool = Field(
        default=True,
        description="是否启用外键约束（仅 SQLite）",
    )
    echo_sql: bool = Field(
        default=False,
        description="是否打印 SQL 语句（调试用途）",
    )
    pool_size: int = Field(
        default=5,
        description="连接池大小",
    )
    max_overflow: int = Field(
        default=10,
        description="最大溢出连接数",
    )

    # 代码生成控制
    generate_model_copy: bool = Field(
        default=True,
        description="是否复制模型文件到输出目录",
    )
    soft_delete_field: str = Field(
        default="is_deleted",
        description="软删除字段名",
    )
    soft_delete_default: bool = Field(
        default=False,
        description="软删除字段默认值",
    )
    timestamp_fields: List[str] = Field(
        default_factory=lambda: ["created_at", "updated_at"],
        description="自动时间戳字段名列表",
    )

    # 代码风格配置
    format_code: bool = Field(
        default=False,
        description="生成后是否自动格式化代码（需要 black）",
    )
    line_length: int = Field(
        default=88,
        description="代码行长度限制（配合 black）",
    )
    include_type_hints: bool = Field(
        default=True,
        description="是否包含完整的类型注解",
    )

    # 安全备份配置
    backup_before_generate: bool = Field(
        default=False,
        description="生成前是否备份现有文件",
    )
    backup_suffix: str = Field(
        default=".bak",
        description="备份文件后缀",
    )

    @field_validator("generators")
    @classmethod
    def validate_generators(cls, v: List[str]) -> List[str]:
        """验证生成器类型是否合法

        检查 generators 列表中的每个值是否在允许的集合中。
        如果包含 "all"，则返回所有生成器类型。

        Args:
            v: 生成器类型列表

        Returns:
            验证后的生成器类型列表

        Raises:
            ValueError: 当包含非法的生成器类型时抛出
        """
        if not v:
            return ["crud", "schemas"]

        # 如果包含 "all"，返回所有类型
        if "all" in v:
            return ["crud", "schemas"]

        # 验证每个生成器类型
        invalid = set(v) - VALID_GENERATORS
        if invalid:
            raise ValueError(
                f"非法的生成器类型: {invalid}. 允许的值: {VALID_GENERATORS}"
            )

        return v

    @field_validator("models_path")
    @classmethod
    def validate_models_path(cls, v: str) -> str:
        """验证模型路径

        检查模型路径是否为有效的文件路径（不支持模块导入路径）。
        路径可以是相对路径或绝对路径。

        Args:
            v: 模型路径字符串

        Returns:
            验证后的模型路径

        Raises:
            ValueError: 当路径格式无效或不存在时抛出
        """
        # 检查是否为模块导入路径格式（包含点但不是以点开头）
        if "." in v and not v.startswith("."):
            # 检查是否看起来像模块路径（如 app.models）
            # 如果路径中包含点且没有斜杠或反斜杠，认为是模块路径
            if "/" not in v and "\\" not in v:
                raise ValueError(
                    f"模型路径不能使用模块导入格式: {v}\n"
                    f"请使用文件路径格式，例如: {v.replace('.', '/')}"
                )

        path = Path(v)

        # 验证路径存在且为目录
        if not path.exists():
            raise ValueError(f"模型路径不存在: {v}")

        if not path.is_dir():
            raise ValueError(f"模型路径必须是目录: {v}")

        return v

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: str) -> str:
        """验证输出目录

        检查输出目录是否有效。如果目录不存在，会尝试创建。

        Args:
            v: 输出目录字符串

        Returns:
            验证后的输出目录

        Raises:
            ValueError: 当路径无效时抛出
        """
        path = Path(v)

        # 如果路径已存在但不是目录，报错
        if path.exists() and not path.is_dir():
            raise ValueError(f"输出路径必须是目录: {v}")

        # 确保目录存在
        path.mkdir(parents=True, exist_ok=True)

        return v

    @field_validator("template_dir")
    @classmethod
    def validate_template_dir(cls, v: Optional[str]) -> Optional[str]:
        """验证模板目录

        如果指定了模板目录，检查该目录是否存在。

        Args:
            v: 模板目录路径，可为 None

        Returns:
            验证后的模板目录路径

        Raises:
            ValueError: 当目录不存在时抛出
        """
        if v is None:
            return v

        path = Path(v)
        if not path.exists():
            raise ValueError(f"模板目录不存在: {v}")
        if not path.is_dir():
            raise ValueError(f"模板路径必须是目录: {v}")

        return v

    @model_validator(mode="after")
    def validate_path_conflict(self) -> "GeneratorConfig":
        """验证模型路径和输出目录是否存在冲突

        如果模型路径位于输出目录内，会自动禁用模型复制功能，
        以避免出现两份模型文件的问题。

        Returns:
            GeneratorConfig 实例
        """
        models_path = Path(self.models_path).resolve()
        output_dir = Path(self.output_dir).resolve()

        try:
            # 检查 models_path 是否是 output_dir 的子目录
            models_path.relative_to(output_dir)
            # 路径冲突时，自动禁用模型复制
            if self.generate_model_copy:
                self.generate_model_copy = False
        except ValueError:
            # relative_to 抛出 ValueError 表示不是子目录，这是正常情况
            pass

        return self


# 默认配置字典（用于创建配置时的默认值）
DEFAULT_CONFIG_DICT = {
    "models_path": "app/models",
    "output_dir": "app/generated",
    "generators": ["crud", "schemas"],
    "template_dir": None,
    "crud_suffix": "CRUD",
    "schema_suffix": "Schema",
    "schema_create_suffix": "Create",
    "schema_update_suffix": "Update",
    "schema_response_suffix": "Response",
    "use_async": True,
    "include_docstrings": True,
    "pagination_default_size": 100,
    "pagination_max_size": 1000,
    "type_mapping": {},
    "exclude_models": [],
    "snapshot_file": ".sqlmodel-crud-snapshot.json",
    "generate_data_layer": True,
    "data_layer_db_name": "app.db",
    # 数据库连接配置
    "enable_foreign_keys": True,
    "echo_sql": False,
    "pool_size": 5,
    "max_overflow": 10,
    # 代码生成控制
    "generate_model_copy": True,
    "soft_delete_field": "is_deleted",
    "soft_delete_default": False,
    "timestamp_fields": ["created_at", "updated_at"],
    # 代码风格配置
    "format_code": False,
    "line_length": 88,
    "include_type_hints": True,
    # 安全备份配置
    "backup_before_generate": False,
    "backup_suffix": ".bak",
}


def get_default_config() -> GeneratorConfig:
    """获取默认配置实例

    延迟创建配置实例，避免在模块导入时验证路径。
    如果默认路径不存在，会使用当前目录作为回退。

    Returns:
        GeneratorConfig 实例
    """
    import os

    config_dict = DEFAULT_CONFIG_DICT.copy()

    # 检查默认路径是否存在，如果不存在则使用当前目录
    if not os.path.exists(config_dict["models_path"]):
        config_dict["models_path"] = "."

    # 确保输出目录存在
    os.makedirs(config_dict["output_dir"], exist_ok=True)

    return GeneratorConfig(**config_dict)


# 默认配置实例（延迟创建）
DEFAULT_CONFIG = None  # 使用 get_default_config() 获取


def _load_toml_file(path: str) -> Optional[Dict]:
    """加载 TOML 文件

    尝试使用 Python 3.11+ 内置的 tomllib，如果不存在则尝试使用 tomli。

    Args:
        path: TOML 文件路径

    Returns:
        解析后的字典，如果文件不存在或解析失败则返回 None
    """
    file_path = Path(path)
    if not file_path.exists():
        return None

    try:
        # 尝试使用 Python 3.11+ 内置的 tomllib
        import tomllib

        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        # 回退到 tomli
        try:
            import tomli

            with open(file_path, "rb") as f:
                return tomli.load(f)
        except ImportError:
            return None
    except Exception:
        return None


def _get_config_from_dict(data: Dict) -> Optional[GeneratorConfig]:
    """从字典创建配置对象

    从配置字典中提取 sqlmodel-crud 相关的配置项。

    Args:
        data: 配置字典

    Returns:
        GeneratorConfig 实例，如果没有找到配置则返回 None
    """
    # 尝试从 tool.sqlmodel-crud 或 sqlmodel-crud 键获取配置
    config_data = data.get("tool", {}).get("sqlmodel-crud", {})
    if not config_data:
        config_data = data.get("sqlmodel-crud", {})

    if not config_data:
        return None

    try:
        return GeneratorConfig(**config_data)
    except Exception:
        return None


def load_config_from_pyproject() -> Optional[GeneratorConfig]:
    """从 pyproject.toml 加载配置

    在当前工作目录及父目录中查找 pyproject.toml 文件，
    并从中读取 [tool.sqlmodel-crud] 部分的配置。

    Returns:
        GeneratorConfig 实例，如果未找到配置则返回 None

    示例:
        >>> config = load_config_from_pyproject()
        >>> if config:
        ...     print(f"模型路径: {config.models_path}")

    pyproject.toml 配置示例:
        ```toml
        [tool.sqlmodel-crud]
        models_path = "app/models"
        output_dir = "app/generated"
        generators = ["crud", "schemas"]
        crud_suffix = "CRUD"
        schema_suffix = "Schema"
        exclude_models = ["BaseModel", "AuditLog"]
        ```
    """
    # 在当前目录及父目录中查找 pyproject.toml
    current_dir = Path.cwd()
    for parent in [current_dir, *current_dir.parents]:
        pyproject_path = parent / "pyproject.toml"
        if pyproject_path.exists():
            data = _load_toml_file(str(pyproject_path))
            if data:
                return _get_config_from_dict(data)

    return None


def load_config_from_file(path: str) -> Optional[GeneratorConfig]:
    """从指定配置文件加载配置

    从指定的 TOML 配置文件加载配置。配置文件应该包含 [sqlmodel-crud] 部分
    或直接包含配置项。

    Args:
        path: 配置文件路径

    Returns:
        GeneratorConfig 实例，如果文件不存在或解析失败则返回 None

    Raises:
        FileNotFoundError: 当配置文件不存在时抛出

    示例:
        >>> config = load_config_from_file(".sqlmodel-crud.toml")
        >>> print(config.models_path)

    配置文件示例 (.sqlmodel-crud.toml):
        ```toml
        [sqlmodel-crud]
        models_path = "app/models"
        output_dir = "app/generated"
        generators = ["crud", "schemas"]
        crud_suffix = "CRUD"
        schema_suffix = "Schema"
        ```
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    data = _load_toml_file(path)
    if not data:
        return None

    return _get_config_from_dict(data)


def _load_from_env() -> Dict[str, Any]:
    """从环境变量加载配置

    读取以 SQLMODEL_CRUD_ 为前缀的环境变量，并将其转换为配置字典。
    环境变量名转换为小写后作为配置键，值进行适当类型转换。

    Returns:
        配置字典

    支持的环境变量:
        - SQLMODEL_CRUD_MODELS_PATH: 模型路径
        - SQLMODEL_CRUD_OUTPUT_DIR: 输出目录
        - SQLMODEL_CRUD_GENERATORS: 生成器类型（逗号分隔）
        - SQLMODEL_CRUD_TEMPLATE_DIR: 模板目录
        - SQLMODEL_CRUD_CRUD_SUFFIX: CRUD 后缀
        - SQLMODEL_CRUD_SCHEMA_SUFFIX: Schema 后缀
        - SQLMODEL_CRUD_EXCLUDE_MODELS: 排除模型（逗号分隔）
        - SQLMODEL_CRUD_SNAPSHOT_FILE: 快照文件路径
        - SQLMODEL_CRUD_ENABLE_FOREIGN_KEYS: 启用外键约束 (true/false)
        - SQLMODEL_CRUD_ECHO_SQL: 打印 SQL 语句 (true/false)
        - SQLMODEL_CRUD_POOL_SIZE: 连接池大小
        - SQLMODEL_CRUD_MAX_OVERFLOW: 最大溢出连接数
        - SQLMODEL_CRUD_GENERATE_MODEL_COPY: 复制模型文件 (true/false)
        - SQLMODEL_CRUD_SOFT_DELETE_FIELD: 软删除字段名
        - SQLMODEL_CRUD_FORMAT_CODE: 自动格式化代码 (true/false)
        - SQLMODEL_CRUD_BACKUP_BEFORE_GENERATE: 生成前备份 (true/false)

    示例:
        >>> # 设置环境变量
        >>> import os
        >>> os.environ["SQLMODEL_CRUD_MODELS_PATH"] = "custom/models"
        >>> os.environ["SQLMODEL_CRUD_GENERATORS"] = "crud,schemas"
        >>>
        >>> # 加载环境变量配置
        >>> env_config = _load_from_env()
        >>> print(env_config)
        {'models_path': 'custom/models', 'generators': ['crud', 'schemas']}
    """
    config = {}
    prefix = "SQLMODEL_CRUD_"

    # 映射环境变量名到配置键
    mappings = {
        "MODELS_PATH": "models_path",
        "OUTPUT_DIR": "output_dir",
        "GENERATORS": "generators",
        "TEMPLATE_DIR": "template_dir",
        "CRUD_SUFFIX": "crud_suffix",
        "SCHEMA_SUFFIX": "schema_suffix",
        "EXCLUDE_MODELS": "exclude_models",
        "SNAPSHOT_FILE": "snapshot_file",
        "GENERATE_DATA_LAYER": "generate_data_layer",
        "DATA_LAYER_DB_NAME": "data_layer_db_name",
        # 新增配置项
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

    # 布尔类型配置项
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

    # 整数类型配置项
    int_fields = {"pool_size", "max_overflow", "line_length"}

    # 列表类型配置项
    list_fields = {"generators", "exclude_models", "timestamp_fields"}

    for env_key, config_key in mappings.items():
        env_value = os.getenv(f"{prefix}{env_key}")
        if env_value is not None:
            # 处理布尔类型
            if config_key in bool_fields:
                config[config_key] = env_value.lower() in ("true", "1", "yes", "on")
            # 处理整数类型
            elif config_key in int_fields:
                try:
                    config[config_key] = int(env_value)
                except ValueError:
                    continue
            # 处理列表类型
            elif config_key in list_fields:
                config[config_key] = [
                    item.strip() for item in env_value.split(",") if item.strip()
                ]
            else:
                config[config_key] = env_value

    return config


def load_config(
    config_path: Optional[str] = None,
) -> GeneratorConfig:
    """综合加载配置

    按照以下优先级加载配置（从高到低）：
        1. 环境变量（SQLMODEL_CRUD_*）
        2. 指定的配置文件（如果提供了 config_path）
        3. pyproject.toml 配置文件
        4. .sqlmodel-crud.toml 配置文件
        5. 默认配置

    Args:
        config_path: 可选的自定义配置文件路径

    Returns:
        GeneratorConfig 实例

    Raises:
        ValueError: 当配置验证失败时抛出

    示例:
        >>> # 自动加载配置
        >>> config = load_config()
        >>>
        >>> # 从指定文件加载
        >>> config = load_config("custom-config.toml")
    """
    # 从默认配置字典开始
    config_dict = DEFAULT_CONFIG_DICT.copy()

    # 1. 尝试从配置文件加载（优先级：指定文件 > pyproject.toml > .sqlmodel-crud.toml）
    file_config = None

    if config_path:
        # 使用指定的配置文件
        try:
            file_config = load_config_from_file(config_path)
        except FileNotFoundError:
            pass
    else:
        # 尝试 pyproject.toml
        file_config = load_config_from_pyproject()

        # 尝试 .sqlmodel-crud.toml
        if file_config is None:
            try:
                file_config = load_config_from_file(".sqlmodel-crud.toml")
            except FileNotFoundError:
                pass

    if file_config:
        config_dict.update(file_config.model_dump(exclude_unset=True))

    # 2. 环境变量覆盖（最高优先级）
    env_config = _load_from_env()
    config_dict.update(env_config)

    # 创建配置对象（Pydantic 会自动验证）
    config = GeneratorConfig(**config_dict)

    return config
