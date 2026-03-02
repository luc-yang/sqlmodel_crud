"""
代码生成引擎模块。

该模块提供了根据模型元数据生成 CRUD 代码的核心功能。
"""

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, get_origin, get_args
from dataclasses import dataclass
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, PackageLoader

from .scanner import ModelMeta, FieldMeta
from .config import GeneratorConfig
from .exceptions import ValidationError


@dataclass
class GeneratedFile:
    """
    生成的文件信息。

    Attributes:
        file_path: 文件路径
        content: 文件内容
        model_name: 关联的模型名称
        generator_type: 生成器类型（crud/schemas/api）
    """

    file_path: str
    content: str
    model_name: Optional[str] = None
    generator_type: str = ""


class CodeGenerator:
    """
    代码生成器类。

    根据模型元数据生成完整的 CRUD 代码，包括：
    - CRUD 操作类
    - SQLModel 验证模型（Schema）

    Attributes:
        config: 生成器配置对象
        jinja_env: Jinja2 模板环境
        generated_files: 生成的文件列表

    Example:
        >>> config = GeneratorConfig(output_dir="app/generated")
        >>> generator = CodeGenerator(config)
        >>> files = generator.generate([model_meta])
        >>> generator.write_files(files)
    """

    def __init__(self, config: GeneratorConfig):
        """
        初始化代码生成器。

        Args:
            config: 生成器配置对象
        """
        self.config = config
        self.jinja_env = self._setup_jinja_env()
        self.generated_files: List[GeneratedFile] = []

    def _setup_jinja_env(self) -> Environment:
        """
        设置 Jinja2 模板环境。

        支持从自定义模板目录或内置模板加载。

        Returns:
            配置好的 Jinja2 环境对象
        """
        # 确定模板加载器
        if self.config.template_dir:
            # 使用自定义模板目录
            template_dir = Path(self.config.template_dir)
            loader = FileSystemLoader(template_dir)
        else:
            # 使用内置模板
            loader = PackageLoader("sqlmodel_crud", "templates")

        env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

        # 添加自定义过滤器
        env.filters["snake_case"] = self._to_snake_case
        env.filters["pascal_case"] = self._to_pascal_case
        env.filters["camel_case"] = self._to_camel_case

        # 添加全局辅助函数
        env.globals["get_type_import"] = self._get_type_import
        env.globals["format_type"] = self._format_type
        env.globals["now"] = datetime.now
        env.globals["hasattr"] = hasattr
        env.globals["getattr"] = getattr

        return env

    def generate(self, models: List[ModelMeta]) -> List[GeneratedFile]:
        """
        根据模型列表生成所有代码文件。

        Args:
            models: 模型元数据列表

        Returns:
            生成的文件列表
        """
        all_files = []

        # 如果启用了数据层生成，先生成基础设施文件
        if self.config.generate_data_layer:
            data_layer_files = self.generate_data_layer(models)
            all_files.extend(data_layer_files)

        for model in models:
            # 检查模型是否在排除列表中
            if model.name in self.config.exclude_models:
                continue

            # 根据配置的生成器类型生成代码
            if "crud" in self.config.generators or "all" in self.config.generators:
                crud_file = self.generate_crud(model)
                if crud_file:
                    all_files.append(crud_file)

            # Schema 生成已禁用 - PyQt 桌面应用直接使用原始模型类
            # if "schemas" in self.config.generators or "all" in self.config.generators:
            #     schema_files = self.generate_schemas(model)
            #     all_files.extend(schema_files)

        self.generated_files = all_files
        return all_files

    def generate_data_layer(self, models: List[ModelMeta]) -> List[GeneratedFile]:
        """
        生成数据层基础设施文件。

        包括 config.py、database.py、__init__.py 文件，以及复制 models 文件夹。

        Args:
            models: 模型元数据列表

        Returns:
            生成的文件列表
        """
        files = []

        try:
            # 生成 config.py
            config_file = self.generate_config()
            if config_file:
                files.append(config_file)

            # 生成 database.py
            database_file = self.generate_database()
            if database_file:
                files.append(database_file)

            # 生成 __init__.py
            init_file = self.generate_data_init(models)
            if init_file:
                files.append(init_file)

            # 复制 models 文件夹
            self._copy_models_directory()

        except Exception as e:
            raise ValidationError(f"生成数据层基础设施文件失败: {e}") from e

        return files

    def _copy_models_directory(self) -> None:
        """
        复制 models 文件夹到输出目录。

        确保生成的数据层文件夹可以独立工作，无需依赖原始 models 路径。

        注意:
            - 如果输出目录中已存在 models 文件夹，会跳过复制
            - 复制的 models 文件夹保持原始结构
            - 建议在配置中设置 output_dir 与 models_path 不重叠
            - 可以通过配置 generate_model_copy=False 禁用复制
        """
        # 如果配置禁用模型复制，直接返回
        if not getattr(self.config, "generate_model_copy", True):
            return

        try:
            # 获取源 models 路径和目标路径
            source_models = Path(self.config.models_path).resolve()
            output_dir = Path(self.config.output_dir).resolve()
            target_models = output_dir / "models"

            # 检查源路径是否存在
            if not source_models.exists():
                return

            # 检查是否会导致路径重叠（源路径是目标路径的子目录）
            if source_models.is_relative_to(output_dir):
                # 如果 models 已经在输出目录中，无需复制，但提醒用户
                print(
                    f"⚠️  警告: models_path ({source_models}) 位于 output_dir ({output_dir}) 内"
                )
                print(f"   这可能导致生成的代码与原始模型文件冲突。")
                print(f"   建议将 output_dir 设置为与 models_path 不同的目录。")
                print(
                    f"   例如: models_path='app/data/models', output_dir='app/generated'"
                )
                return

            # 如果目标已存在，跳过复制
            if target_models.exists():
                return

            # 复制 models 文件夹
            if source_models.is_dir():
                shutil.copytree(source_models, target_models)
            else:
                # 如果是单个文件，复制文件
                target_models.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_models, target_models)

        except Exception as e:
            # 复制失败不阻止其他文件生成，只记录警告
            import warnings

            warnings.warn(f"复制 models 文件夹失败: {e}", RuntimeWarning)

    def generate_config(self) -> Optional[GeneratedFile]:
        """
        生成数据库配置模块 config.py。

        Returns:
            生成的文件信息，如果生成失败返回 None
        """
        try:
            # 准备模板上下文
            # db_dir 默认为 None，表示使用模块所在目录
            context = {
                "config": self.config,
                "db_name": self.config.data_layer_db_name,
                "db_dir": None,
            }

            # 渲染模板
            content = self._render_template("config.py.j2", context)

            return GeneratedFile(
                file_path="config.py",
                content=content,
                model_name=None,
                generator_type="data_layer",
            )

        except Exception as e:
            raise ValidationError(f"生成 config.py 失败: {e}") from e

    def generate_database(self) -> Optional[GeneratedFile]:
        """
        生成数据库初始化模块 database.py。

        Returns:
            生成的文件信息，如果生成失败返回 None
        """
        try:
            # 准备模板上下文
            context = {
                "config": self.config,
            }

            # 渲染模板
            content = self._render_template("database.py.j2", context)

            return GeneratedFile(
                file_path="database.py",
                content=content,
                model_name=None,
                generator_type="data_layer",
            )

        except Exception as e:
            raise ValidationError(f"生成 database.py 失败: {e}") from e

    def generate_data_init(self, models: List[ModelMeta]) -> Optional[GeneratedFile]:
        """
        生成数据层统一导出模块 __init__.py。

        Args:
            models: 模型元数据列表

        Returns:
            生成的文件信息，如果生成失败返回 None
        """
        try:
            # 过滤掉排除的模型
            filtered_models = [
                model
                for model in models
                if model.name not in self.config.exclude_models
            ]

            # 准备模板上下文
            context = {
                "config": self.config,
                "models": filtered_models,
            }

            # 渲染模板
            content = self._render_template("data_init.py.j2", context)

            return GeneratedFile(
                file_path="__init__.py",
                content=content,
                model_name=None,
                generator_type="data_layer",
            )

        except Exception as e:
            raise ValidationError(f"生成 __init__.py 失败: {e}") from e

    def generate_crud(self, model: ModelMeta) -> Optional[GeneratedFile]:
        """
        生成单个模型的 CRUD 类代码。

        Args:
            model: 模型元数据

        Returns:
            生成的文件信息，如果生成失败返回 None
        """
        try:
            # 获取主键信息
            primary_key_field = self._get_primary_key_field(model)
            if not primary_key_field:
                raise ValueError(f"模型 {model.name} 没有主键字段")

            # 准备模板上下文
            context = {
                "model": model,
                "config": self.config,
                "model_name": model.name,
                "crud_class_name": f"{model.name}{self.config.crud_suffix}",
                "table_name": model.table_name or self._to_snake_case(model.name),
                "primary_key": primary_key_field.name,
                "primary_key_type": self._format_type(primary_key_field.python_type),
                "file_header": self._generate_file_header(model.name, "CRUD"),
                # 索引相关信息
                "indexed_fields": self._get_indexed_fields(model),
                "unique_fields": self._get_unique_fields(model),
                "has_partial_indexes": self._has_partial_indexes(model),
            }

            # 渲染模板
            content = self._render_template("crud.py.j2", context)

            # 确定输出路径
            file_path = self._get_output_path("crud", model.name)

            return GeneratedFile(
                file_path=str(file_path),
                content=content,
                model_name=model.name,
                generator_type="crud",
            )

        except Exception as e:
            raise ValidationError(
                f"生成 CRUD 代码失败: {e}", context={"model": model.name}
            ) from e

    def generate_schemas(self, model: ModelMeta) -> List[GeneratedFile]:
        """
        生成单个模型的验证模型代码（Create/Update/Response）。

        Args:
            model: 模型元数据

        Returns:
            生成的文件列表
        """
        files = []

        try:
            # 获取主键信息
            primary_key_field = self._get_primary_key_field(model)
            primary_key_type = "int"  # 默认类型
            if primary_key_field:
                primary_key_type = self._format_type(primary_key_field.python_type)

            # 准备模板上下文
            context = {
                "model": model,
                "config": self.config,
                "model_name": model.name,
                "primary_key_type": primary_key_type,
                "file_header": self._generate_file_header(model.name, "Schemas"),
            }

            # 渲染模板
            content = self._render_template("schemas.py.j2", context)

            # 确定输出路径
            file_path = self._get_output_path("schemas", model.name)

            files.append(
                GeneratedFile(
                    file_path=str(file_path),
                    content=content,
                    model_name=model.name,
                    generator_type="schemas",
                )
            )

        except Exception as e:
            raise ValidationError(
                f"生成 Schema 代码失败: {e}", context={"model": model.name}
            ) from e

        return files

    def write_files(self, files: List[GeneratedFile], dry_run: bool = False) -> None:
        """
        将生成的文件写入磁盘。

        Args:
            files: 生成的文件列表
            dry_run: 如果为 True，只打印文件信息而不实际写入
        """
        output_dir = Path(self.config.output_dir)
        formatted_files = []

        for file in files:
            file_path = output_dir / file.file_path

            if dry_run:
                print(f"[DRY RUN] 将生成文件: {file_path}")
                print(f"  - 模型: {file.model_name}")
                print(f"  - 类型: {file.generator_type}")
                print(f"  - 内容长度: {len(file.content)} 字符")
                continue

            # 创建目录
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 备份现有文件（如果启用）
            if self.config.backup_before_generate and file_path.exists():
                backup_path = file_path.with_suffix(
                    file_path.suffix + self.config.backup_suffix
                )
                shutil.copy2(file_path, backup_path)
                print(f"  📦 已备份: {backup_path}")

            # 写入文件
            file_path.write_text(file.content, encoding="utf-8")
            print(f"已生成文件: {file_path}")
            formatted_files.append(file_path)

        # 自动格式化代码（如果启用）
        if self.config.format_code and formatted_files:
            self._format_files(formatted_files)

    def _format_files(self, file_paths: List[Path]) -> None:
        """
        使用 black 格式化生成的代码文件。

        Args:
            file_paths: 需要格式化的文件路径列表
        """
        try:
            import subprocess
            import sys

            # 检查 black 是否安装
            result = subprocess.run(
                [sys.executable, "-m", "black", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print("  ⚠️  black 未安装，跳过代码格式化")
                print("     安装命令: uv add --dev black 或 pip install black")
                return

            # 格式化文件
            cmd = [
                sys.executable,
                "-m",
                "black",
                "--line-length",
                str(self.config.line_length),
            ] + [str(p) for p in file_paths]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"  ✨ 已格式化 {len(file_paths)} 个文件")
            else:
                print(f"  ⚠️  格式化失败: {result.stderr}")

        except Exception as e:
            print(f"  ⚠️  格式化时出错: {e}")

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        渲染 Jinja2 模板。

        Args:
            template_name: 模板文件名
            context: 模板上下文数据

        Returns:
            渲染后的代码字符串

        Raises:
            TemplateNotFound: 当模板文件不存在时抛出
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def _get_output_path(self, generator_type: str, model_name: str) -> Path:
        """
        获取输出文件路径。

        使用固定的子目录结构：
        - crud/ 用于 CRUD 代码
        - schemas/ 用于 Schema 代码

        Args:
            generator_type: 生成器类型（crud/schemas）
            model_name: 模型名称

        Returns:
            输出文件路径
        """
        snake_name = self._to_snake_case(model_name)

        # 使用固定的子目录名称
        if generator_type == "crud":
            subdir = "crud"
        elif generator_type == "schemas":
            subdir = "schemas"
        else:
            subdir = generator_type

        return Path(subdir) / f"{snake_name}.py"

    def _get_primary_key_field(self, model: ModelMeta) -> Optional[FieldMeta]:
        """
        获取模型的主键字段。

        Args:
            model: 模型元数据

        Returns:
            主键字段元数据，如果没有则返回 None
        """
        for field in model.fields:
            if field.primary_key:
                return field

        # 如果没有标记为主键的字段，尝试查找名为 id 的字段
        for field in model.fields:
            if field.name == "id":
                return field

        return None

    def _get_indexed_fields(self, model: ModelMeta) -> List[FieldMeta]:
        """
        获取模型的所有索引字段。

        Args:
            model: 模型元数据

        Returns:
            索引字段列表
        """
        return [f for f in model.fields if f.index]

    def _get_unique_fields(self, model: ModelMeta) -> List[FieldMeta]:
        """
        获取模型的所有唯一字段。

        Args:
            model: 模型元数据

        Returns:
            唯一字段列表
        """
        return [f for f in model.fields if f.unique]

    def _has_partial_indexes(self, model: ModelMeta) -> bool:
        """
        检查模型是否有部分索引。

        Args:
            model: 模型元数据

        Returns:
            如果有部分索引返回 True
        """
        for idx in model.indexes:
            if "where" in idx:
                return True
        return False

    def _get_type_import(self, python_type: Any) -> str:
        """
        根据 Python 类型返回导入语句。

        Args:
            python_type: Python 类型

        Returns:
            导入语句字符串
        """
        # 处理 Optional[T] 类型
        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Union and len(args) == 2 and type(None) in args:
            python_type = args[0] if args[1] is type(None) else args[1]

        # 处理 List[T] 类型
        if origin is list:
            return "from typing import List"

        # 处理 Dict 类型
        if origin is dict:
            return "from typing import Dict"

        # 处理 Optional 类型
        if origin is Union:
            return "from typing import Union"

        # 映射需要导入的类型
        import_map = {
            "datetime": "from datetime import datetime",
            "date": "from datetime import date",
            "time": "from datetime import time",
            "Decimal": "from decimal import Decimal",
            "UUID": "from uuid import UUID",
        }

        type_name = getattr(python_type, "__name__", str(python_type))
        return import_map.get(type_name, "")

    def _format_type(self, python_type: Any) -> str:
        """
        格式化类型注解字符串。

        Args:
            python_type: Python 类型

        Returns:
            格式化后的类型字符串
        """
        if python_type is None:
            return "Any"

        # 处理 Optional[T] 类型
        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Union:
            # 处理 Optional[T] = Union[T, None]
            if len(args) == 2 and type(None) in args:
                inner_type = args[0] if args[1] is type(None) else args[1]
                return f"Optional[{self._format_type(inner_type)}]"
            else:
                # 普通 Union 类型
                type_args = ", ".join(self._format_type(arg) for arg in args)
                return f"Union[{type_args}]"

        # 处理 List[T] 类型
        if origin is list:
            if args:
                return f"List[{self._format_type(args[0])}]"
            return "List"

        # 处理 Dict[K, V] 类型
        if origin is dict:
            if args and len(args) == 2:
                return (
                    f"Dict[{self._format_type(args[0])}, {self._format_type(args[1])}]"
                )
            return "Dict"

        # 基本类型
        type_map = {
            str: "str",
            int: "int",
            float: "float",
            bool: "bool",
        }

        if python_type in type_map:
            return type_map[python_type]

        # 返回类型的名称
        return getattr(python_type, "__name__", str(python_type))

    def _to_snake_case(self, name: str) -> str:
        """
        将字符串转换为蛇形命名（snake_case）。

        Args:
            name: 原始字符串

        Returns:
            蛇形命名字符串
        """
        # 处理驼峰命名
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    def _to_pascal_case(self, name: str) -> str:
        """
        将字符串转换为帕斯卡命名（PascalCase）。

        Args:
            name: 原始字符串

        Returns:
            帕斯卡命名字符串
        """
        return "".join(word.capitalize() for word in name.split("_"))

    def _to_camel_case(self, name: str) -> str:
        """
        将字符串转换为驼峰命名（camelCase）。

        Args:
            name: 原始字符串

        Returns:
            驼峰命名字符串
        """
        words = name.split("_")
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])

    def _generate_file_header(self, model_name: str, file_type: str) -> str:
        """
        生成文件头注释。

        Args:
            model_name: 模型名称
            file_type: 文件类型

        Returns:
            文件头注释字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f'''"""
该文件由 SQLModel CRUD 生成器自动生成。

模型: {model_name}
类型: {file_type}
生成时间: {timestamp}

警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""
'''


# 兼容性别名
CRUDGenerator = CodeGenerator


def generate(
    models_path: str,
    output_dir: str,
    generators: Optional[List[str]] = None,
    *,
    use_async: bool = False,
    crud_suffix: str = "CRUD",
    schema_create_suffix: str = "Create",
    schema_update_suffix: str = "Update",
    schema_response_suffix: str = "Response",
    exclude_models: Optional[List[str]] = None,
    dry_run: bool = False,
) -> List[GeneratedFile]:
    """
    便捷代码生成函数

    一键完成模型扫描和代码生成，无需手动创建 ModelScanner 和 CodeGenerator 实例。

    Args:
        models_path: 模型扫描路径（模块路径或文件路径）
        output_dir: 代码输出目录
        generators: 生成器类型列表，默认为 ["crud", "schemas"]
        use_async: 是否生成异步代码，默认为 False
        crud_suffix: CRUD 类后缀，默认为 "CRUD"
        schema_create_suffix: Schema 创建类后缀，默认为 "Create"
        schema_update_suffix: Schema 更新类后缀，默认为 "Update"
        schema_response_suffix: Schema 响应类后缀，默认为 "Response"
        exclude_models: 排除的模型列表
        dry_run: 是否为预览模式（不实际写入文件）

    Returns:
        生成的文件列表

    Raises:
        ValueError: 当模型路径不存在时抛出
        ValidationError: 当生成代码失败时抛出

    示例:
        >>> # 最简单的用法
        >>> files = generate("app/models", "app/generated")
        >>>
        >>> # 完整配置
        >>> files = generate(
        ...     models_path="app/models",
        ...     output_dir="app/generated",
        ...     generators=["crud", "schemas"],
        ...     use_async=False,
        ...     exclude_models=["BaseModel"]
        ... )
        >>>
        >>> # 预览模式
        >>> files = generate("app/models", "app/generated", dry_run=True)
        >>> for f in files:
        ...     print(f"将生成: {f.file_path}")
    """
    from .scanner import ModelScanner

    if generators is None:
        generators = ["crud", "schemas"]

    # 检查路径冲突
    models_path_obj = Path(models_path).resolve()
    output_dir_obj = Path(output_dir).resolve()

    if models_path_obj.is_relative_to(output_dir_obj):
        print("⚠️  警告: models_path 位于 output_dir 内，这会导致循环导入问题！")
        print(f"   models_path: {models_path_obj}")
        print(f"   output_dir: {output_dir_obj}")
        print("   建议修改配置，确保 models_path 和 output_dir 不重叠。")
        print("   例如:")
        print("     - models_path='app/data/models', output_dir='app/generated'")
        print("     - models_path='models', output_dir='app/data'")
        raise ValueError(
            f"models_path ({models_path}) 不能位于 output_dir ({output_dir}) 内。"
            "请修改配置确保两者不重叠。"
        )

    # 创建配置
    config = GeneratorConfig(
        models_path=models_path,
        output_dir=output_dir,
        generators=generators,
        use_async=use_async,
        crud_suffix=crud_suffix,
        schema_create_suffix=schema_create_suffix,
        schema_update_suffix=schema_update_suffix,
        schema_response_suffix=schema_response_suffix,
        exclude_models=exclude_models or [],
    )

    # 扫描模型
    scanner = ModelScanner(config)
    models = scanner.scan_directory(models_path)

    if not models:
        return []

    # 生成代码
    generator = CodeGenerator(config)
    files = generator.generate(models)

    # 写入文件
    if not dry_run:
        generator.write_files(files, dry_run=False)

    return files
