"""代码生成引擎模块。"""

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
from .terminal_output import status_prefix


@dataclass
class GeneratedFile:
    """生成的文件信息。"""

    file_path: str
    content: str
    model_name: Optional[str] = None
    generator_type: str = ""


class CodeGenerator:
    """代码生成器类。"""

    def __init__(self, config: GeneratorConfig):
        """初始化代码生成器。"""
        self.config = config
        self.jinja_env = self._setup_jinja_env()
        self.generated_files: List[GeneratedFile] = []

    def _setup_jinja_env(self) -> Environment:
        """设置 Jinja2 模板环境。"""

        if self.config.template_dir:

            template_dir = Path(self.config.template_dir)
            loader = FileSystemLoader(template_dir)
        else:

            loader = PackageLoader("sqlmodel_crud", "templates")

        env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

        env.filters["snake_case"] = self._to_snake_case
        env.filters["pascal_case"] = self._to_pascal_case
        env.filters["camel_case"] = self._to_camel_case

        env.globals["get_type_import"] = self._get_type_import
        env.globals["format_type"] = self._format_type
        env.globals["now"] = datetime.now
        env.globals["hasattr"] = hasattr
        env.globals["getattr"] = getattr

        return env

    def generate(self, models: List[ModelMeta]) -> List[GeneratedFile]:
        """根据模型列表生成所有代码文件。"""
        all_files = []

        if self.config.generate_data_layer:
            data_layer_files = self.generate_data_layer(models)
            all_files.extend(data_layer_files)

        for model in models:

            if model.name in self.config.exclude_models:
                continue

            crud_file = self.generate_crud(model)
            if crud_file:
                all_files.append(crud_file)

        self.generated_files = all_files
        return all_files

    def generate_data_layer(self, models: List[ModelMeta]) -> List[GeneratedFile]:
        """生成数据层基础设施文件。"""
        files = []

        try:

            config_file = self.generate_config()
            if config_file:
                files.append(config_file)

            database_file = self.generate_database()
            if database_file:
                files.append(database_file)

            init_file = self.generate_data_init(models)
            if init_file:
                files.append(init_file)

        except Exception as e:
            raise ValidationError(f"生成数据层基础设施文件失败: {e}") from e

        return files

    def _copy_models_directory(self) -> None:
        """复制 models 文件夹到输出目录。"""

        if not getattr(self.config, "generate_model_copy", True):
            return

        try:

            source_models = Path(self.config.models_path).resolve()
            output_dir = Path(self.config.output_dir).resolve()
            target_models = output_dir / "models"

            if not source_models.exists():
                return

            if source_models.is_relative_to(output_dir):

                warning_prefix = status_prefix("warning")
                print(
                    f"{warning_prefix}  警告: models_path ({source_models}) 位于 output_dir ({output_dir}) 内"
                )
                print(f"   这可能导致生成的代码与原始模型文件冲突。")
                print(f"   建议将 output_dir 设置为与 models_path 不同的目录。")
                print(
                    f"   例如: models_path='app/data/models', output_dir='app/generated'"
                )
                return

            if target_models.exists():
                return

            if source_models.is_dir():
                shutil.copytree(source_models, target_models)
            else:

                target_models.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_models, target_models)

        except Exception as e:

            import warnings

            warnings.warn(f"复制 models 文件夹失败: {e}", RuntimeWarning)

    def generate_config(self) -> Optional[GeneratedFile]:
        """生成数据库配置模块 config.py。"""
        try:

            context = {
                "config": self.config,
                "db_name": self.config.data_layer_db_name,
                "db_dir": None,
            }

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
        """生成数据库初始化模块 database.py。"""
        try:

            context = {
                "config": self.config,
            }

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
        """生成数据层统一导出模块 __init__.py。"""
        try:

            filtered_models = [
                model
                for model in models
                if model.name not in self.config.exclude_models
            ]

            context = {
                "config": self.config,
                "models": filtered_models,
            }

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
        """生成单个模型的 CRUD 类代码。"""
        try:

            primary_key_field = self._get_primary_key_field(model)
            if not primary_key_field:
                raise ValueError(f"模型 {model.name} 没有主键字段")

            context = {
                "model": model,
                "config": self.config,
                "model_name": model.name,
                "crud_class_name": f"{model.name}{self.config.crud_suffix}",
                "table_name": model.table_name or self._to_snake_case(model.name),
                "primary_key": primary_key_field.name,
                "primary_key_type": self._format_type(primary_key_field.python_type),
                "file_header": self._generate_file_header(model.name, "CRUD"),
                "indexed_fields": self._get_indexed_fields(model),
                "unique_fields": self._get_unique_fields(model),
                "has_partial_indexes": self._has_partial_indexes(model),
            }

            content = self._render_template("crud.py.j2", context)

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

    def write_files(self, files: List[GeneratedFile], dry_run: bool = False) -> None:
        """将生成的文件写入磁盘。"""
        output_dir = Path(self.config.output_dir)
        formatted_files = []

        if (
            not dry_run
            and self.config.generate_data_layer
            and any(file.generator_type == "data_layer" for file in files)
        ):
            self._copy_models_directory()

        for file in files:
            file_path = output_dir / file.file_path

            if dry_run:
                print(f"[DRY RUN] 将生成文件: {file_path}")
                print(f"  - 模型: {file.model_name}")
                print(f"  - 类型: {file.generator_type}")
                print(f"  - 内容长度: {len(file.content)} 字符")
                continue

            file_path.parent.mkdir(parents=True, exist_ok=True)

            if self.config.backup_before_generate and file_path.exists():
                backup_path = file_path.with_suffix(
                    file_path.suffix + self.config.backup_suffix
                )
                shutil.copy2(file_path, backup_path)
                print(f"  📦 已备份: {backup_path}")

            file_path.write_text(file.content, encoding="utf-8")
            print(f"已生成文件: {file_path}")
            formatted_files.append(file_path)

        if self.config.format_code and formatted_files:
            self._format_files(formatted_files)

    def _format_files(self, file_paths: List[Path]) -> None:
        """使用 black 格式化生成的代码文件。"""
        try:
            import subprocess
            import sys

            result = subprocess.run(
                [sys.executable, "-m", "black", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  {status_prefix('warning')}  black 未安装，跳过代码格式化")
                print("     安装命令: uv add --dev black 或 pip install black")
                return

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
                print(f"  {status_prefix('success')} 已格式化 {len(file_paths)} 个文件")
            else:
                print(f"  {status_prefix('warning')}  格式化失败: {result.stderr}")

        except Exception as e:
            print(f"  {status_prefix('warning')}  格式化时出错: {e}")

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """渲染 Jinja2 模板。"""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def _get_output_path(self, generator_type: str, model_name: str) -> Path:
        """获取输出文件路径。"""
        snake_name = self._to_snake_case(model_name)

        if generator_type == "crud":
            subdir = "crud"
        else:
            raise ValueError(f"无效的生成器类型: {generator_type}，可选值: crud")

        return Path(subdir) / f"{snake_name}.py"

    def _get_primary_key_field(self, model: ModelMeta) -> Optional[FieldMeta]:
        """获取模型的主键字段。"""
        for field in model.fields:
            if field.primary_key:
                return field

        for field in model.fields:
            if field.name == "id":
                return field

        return None

    def _get_indexed_fields(self, model: ModelMeta) -> List[FieldMeta]:
        """获取模型的所有索引字段。"""
        return [f for f in model.fields if f.index]

    def _get_unique_fields(self, model: ModelMeta) -> List[FieldMeta]:
        """获取模型的所有唯一字段。"""
        return [f for f in model.fields if f.unique]

    def _has_partial_indexes(self, model: ModelMeta) -> bool:
        """检查模型是否有部分索引。"""
        for idx in model.indexes:
            if "where" in idx:
                return True
        return False

    def _get_type_import(self, python_type: Any) -> str:
        """根据 Python 类型返回导入语句。"""

        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Union and len(args) == 2 and type(None) in args:
            python_type = args[0] if args[1] is type(None) else args[1]

        if origin is list:
            return "from typing import List"

        if origin is dict:
            return "from typing import Dict"

        if origin is Union:
            return "from typing import Union"

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
        """格式化类型注解字符串。"""
        if python_type is None:
            return "Any"

        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Union:

            if len(args) == 2 and type(None) in args:
                inner_type = args[0] if args[1] is type(None) else args[1]
                return f"Optional[{self._format_type(inner_type)}]"
            else:

                type_args = ", ".join(self._format_type(arg) for arg in args)
                return f"Union[{type_args}]"

        if origin is list:
            if args:
                return f"List[{self._format_type(args[0])}]"
            return "List"

        if origin is dict:
            if args and len(args) == 2:
                return (
                    f"Dict[{self._format_type(args[0])}, {self._format_type(args[1])}]"
                )
            return "Dict"

        type_map = {
            str: "str",
            int: "int",
            float: "float",
            bool: "bool",
        }

        if python_type in type_map:
            return type_map[python_type]

        return getattr(python_type, "__name__", str(python_type))

    def _to_snake_case(self, name: str) -> str:
        """将字符串转换为蛇形命名（snake_case）。"""

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    def _to_pascal_case(self, name: str) -> str:
        """将字符串转换为帕斯卡命名（PascalCase）。"""
        return "".join(word.capitalize() for word in name.split("_"))

    def _to_camel_case(self, name: str) -> str:
        """将字符串转换为驼峰命名（camelCase）。"""
        words = name.split("_")
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])

    def _generate_file_header(self, model_name: str, file_type: str) -> str:
        """生成文件头注释。"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f'''"""
该文件由 SQLModel CRUD 生成器自动生成。

模型: {model_name}
类型: {file_type}
生成时间: {timestamp}

警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""
'''


def generate(
    models_path: str,
    output_dir: str,
    *,
    use_async: bool = False,
    crud_suffix: str = "CRUD",
    exclude_models: Optional[List[str]] = None,
    dry_run: bool = False,
) -> List[GeneratedFile]:
    """便捷代码生成函数"""
    from .scanner import ModelScanner

    models_path_obj = Path(models_path).resolve()
    output_dir_obj = Path(output_dir).resolve()

    if models_path_obj.is_relative_to(output_dir_obj):
        print(
            f"{status_prefix('warning')}  警告: models_path 位于 output_dir 内，这会导致循环导入问题！"
        )
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

    config = GeneratorConfig(
        models_path=models_path,
        output_dir=output_dir,
        use_async=use_async,
        crud_suffix=crud_suffix,
        exclude_models=exclude_models or [],
    )

    scanner = ModelScanner(config)
    models = scanner.scan(models_path)

    if not models:
        return []

    generator = CodeGenerator(config)
    files = generator.generate(models)

    if not dry_run:
        generator.write_files(files, dry_run=False)

    return files
