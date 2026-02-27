"""
SQLModel CRUD 代码生成器 CLI 模块

提供命令行接口用于初始化项目和生成 CRUD 代码。

主要命令:
    - init: 初始化项目，创建配置文件和目录结构
    - generate: 扫描模型并生成代码
    - version: 显示版本信息

示例:
    >>> # 初始化项目
    >>> sqlmodel-crud init --template basic
    >>>
    >>> # 生成代码
    >>> sqlmodel-crud generate --models-path app/models --output-dir app/generated
    >>>
    >>> # 预览模式
    >>> sqlmodel-crud generate --dry-run
"""

import typer
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .scanner import ModelScanner
from .generator import CodeGenerator
from .detector import ChangeDetector

# 版本信息
__version__ = "1.1.0"
__author__ = "LucYang 杨艺斌"

# 创建 Typer 应用
app = typer.Typer(
    help="SQLModel CRUD 代码生成器",
    no_args_is_help=True,
)

# 创建 Rich 控制台
console = Console()


def print_success(message: str) -> None:
    """
    打印成功消息（绿色）

    Args:
        message: 要打印的消息
    """
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """
    打印错误消息（红色）

    Args:
        message: 要打印的消息
    """
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """
    打印警告消息（黄色）

    Args:
        message: 要打印的消息
    """
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    """
    打印信息消息（蓝色）

    Args:
        message: 要打印的消息
    """
    console.print(f"[blue]ℹ[/blue] {message}")


@app.command()
def init(
    template: str = typer.Option(
        "basic",
        "--template",
        "-t",
        help="模板类型 (basic/full)",
    ),
    models_path: str = typer.Option(
        "app/models",
        "--models-path",
        "-m",
        help="模型路径",
    ),
    output_dir: str = typer.Option(
        "app/generated",
        "--output-dir",
        "-o",
        help="输出目录",
    ),
    config_file: str = typer.Option(
        ".sqlmodel-crud.toml",
        "--config",
        "-c",
        help="配置文件名",
    ),
) -> None:
    """
    初始化项目，创建配置文件和目录结构

    此命令会:
        - 创建配置文件 (.sqlmodel-crud.toml 或 pyproject.toml)
        - 创建模型目录
        - 创建输出目录
        - 生成示例模型文件

    示例:
        $ sqlmodel-crud init
        $ sqlmodel-crud init --template full --models-path src/models
    """
    print_info("开始初始化项目...")

    # 验证模板类型
    if template not in ("basic", "full"):
        print_error(f"无效的模板类型: {template}。可选值: basic, full")
        raise typer.Exit(code=1)

    # 创建目录
    models_dir = Path(models_path)
    output_path = Path(output_dir)

    try:
        # 创建模型目录
        models_dir.mkdir(parents=True, exist_ok=True)
        print_success(f"创建模型目录: {models_dir}")

        # 创建输出目录
        output_path.mkdir(parents=True, exist_ok=True)
        print_success(f"创建输出目录: {output_path}")

        # 创建子目录
        for subdir in ("crud", "schemas"):
            (output_path / subdir).mkdir(exist_ok=True)
        print_success("创建输出子目录: crud, schemas")

    except OSError as e:
        print_error(f"创建目录失败: {e}")
        raise typer.Exit(code=1)

    # 创建配置文件
    config_path = Path(config_file)

    if config_file.endswith("pyproject.toml"):
        # 创建 pyproject.toml 配置
        _create_pyproject_config(config_path, models_path, output_dir, template)
    else:
        # 创建独立的 .sqlmodel-crud.toml 配置
        _create_standalone_config(config_path, models_path, output_dir, template)

    # 生成示例模型文件
    example_model_path = models_dir / "example.py"
    if not example_model_path.exists():
        _create_example_model(example_model_path, template)
        print_success(f"创建示例模型文件: {example_model_path}")

    # 创建 __init__.py
    init_file = models_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""SQLModel models module."""\n', encoding="utf-8")
        print_success(f"创建初始化文件: {init_file}")

    # 显示完成信息
    console.print()
    console.print(
        Panel(
            f"[bold green]项目初始化完成！[/bold green]\n\n"
            f"配置文件: [cyan]{config_path}[/cyan]\n"
            f"模型路径: [cyan]{models_path}[/cyan]\n"
            f"输出目录: [cyan]{output_dir}[/cyan]\n\n"
            f"下一步:\n"
            f"  1. 在 [cyan]{models_path}[/cyan] 中定义你的 SQLModel 模型\n"
            f"  2. 运行 [bold]sqlmodel-crud generate[/bold] 生成代码",
            title="SQLModel CRUD Generator",
            border_style="green",
        )
    )


def _create_pyproject_config(
    config_path: Path,
    models_path: str,
    output_dir: str,
    template: str,
) -> None:
    """
    创建 pyproject.toml 配置文件

    Args:
        config_path: 配置文件路径
        models_path: 模型路径
        output_dir: 输出目录
        template: 模板类型
    """
    # 检查是否已存在 pyproject.toml
    if config_path.exists():
        # 追加配置到现有文件
        content = config_path.read_text(encoding="utf-8")
        if "[tool.sqlmodel-crud]" in content:
            print_warning("pyproject.toml 中已存在 SQLModel CRUD 配置")
            return

        config_section = f"""

[tool.sqlmodel-crud]
models_path = "{models_path}"
output_dir = "{output_dir}"
generators = ["crud", "schemas"]
crud_suffix = "CRUD"
schema_suffix = "Schema"
exclude_models = []
"""
        content += config_section
        config_path.write_text(content, encoding="utf-8")
    else:
        # 创建新的 pyproject.toml
        content = f"""[tool.sqlmodel-crud]
models_path = "{models_path}"
output_dir = "{output_dir}"
generators = ["crud", "schemas"]
crud_suffix = "CRUD"
schema_suffix = "Schema"
exclude_models = []
"""
        config_path.write_text(content, encoding="utf-8")

    print_success(f"创建配置文件: {config_path}")


def _create_standalone_config(
    config_path: Path,
    models_path: str,
    output_dir: str,
    template: str,
) -> None:
    """
    创建独立的 .sqlmodel-crud.toml 配置文件

    Args:
        config_path: 配置文件路径
        models_path: 模型路径
        output_dir: 输出目录
        template: 模板类型
    """
    if config_path.exists():
        print_warning(f"配置文件已存在: {config_path}")
        return

    # 根据模板类型生成配置
    if template == "full":
        content = f"""[sqlmodel-crud]
models_path = "{models_path}"
output_dir = "{output_dir}"
generators = ["crud", "schemas"]
crud_suffix = "CRUD"
schema_suffix = "Schema"
schema_create_suffix = "Create"
schema_update_suffix = "Update"
schema_response_suffix = "Response"
use_async = true
include_docstrings = true
pagination_default_size = 100
pagination_max_size = 1000
exclude_models = []
snapshot_file = ".sqlmodel-crud-snapshot.json"

# 数据层基础设施文件生成配置
# 数据库文件将直接放在 output_dir 下
generate_data_layer = true
data_layer_db_name = "app.db"
"""
    else:
        content = f"""[sqlmodel-crud]
models_path = "{models_path}"
output_dir = "{output_dir}"
generators = ["crud", "schemas"]

# 数据层基础设施文件生成配置（开箱即用）
# 数据库文件将直接放在 output_dir 下
generate_data_layer = true
data_layer_db_name = "app.db"
"""

    config_path.write_text(content, encoding="utf-8")
    print_success(f"创建配置文件: {config_path}")


def _create_example_model(file_path: Path, template: str) -> None:
    """
    创建示例模型文件

    Args:
        file_path: 文件路径
        template: 模板类型
    """
    content = '''"""
示例 SQLModel 模型

此文件展示了如何定义 SQLModel 模型，
生成器会根据这些模型自动生成 CRUD 代码。
"""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """用户模型"""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    email: str = Field(unique=True, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Item(SQLModel, table=True):
    """物品模型"""

    __tablename__ = "items"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    description: Optional[str] = Field(default=None)
    price: float = Field(ge=0)
    owner_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
'''

    file_path.write_text(content, encoding="utf-8")


@app.command()
def generate(
    models_path: Optional[str] = typer.Option(
        None,
        "--models-path",
        "-m",
        help="模型路径（覆盖配置）",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="输出目录（覆盖配置）",
    ),
    generators: Optional[str] = typer.Option(
        None,
        "--generators",
        "-g",
        help="生成器类型，逗号分隔（crud/schemas/all）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="预览模式，不实际写入文件",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制重新生成所有代码",
    ),
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="指定配置文件路径",
    ),
) -> None:
    """
    扫描模型并生成代码

    此命令会:
        - 加载配置
        - 扫描模型
        - 检测变更
        - 生成代码
        - 显示进度和摘要
        - 保存快照

    示例:
        $ sqlmodel-crud generate
        $ sqlmodel-crud generate --models-path src/models --dry-run
        $ sqlmodel-crud generate --generators crud,schemas --force
    """
    print_info("开始生成代码...")

    # 加载配置
    try:
        config = load_config(config_path)
        print_success("加载配置完成")
    except Exception as e:
        print_error(f"加载配置失败: {e}")
        raise typer.Exit(code=1)

    # 应用命令行参数覆盖
    if models_path:
        config.models_path = models_path
    if output_dir:
        config.output_dir = output_dir
    if generators:
        config.generators = [g.strip() for g in generators.split(",")]

    # 验证模型路径
    models_dir = Path(config.models_path)
    if not models_dir.exists():
        print_error(f"模型路径不存在: {config.models_path}")
        raise typer.Exit(code=1)

    # 创建输出目录
    output_path = Path(config.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 初始化组件
    scanner = ModelScanner(config)
    detector = ChangeDetector(config.snapshot_file)
    generator = CodeGenerator(config)

    # 扫描模型
    print_info("扫描模型中...")
    models = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("扫描模型文件...", total=None)

        try:
            models = scanner.scan_module(str(models_dir))
            progress.update(task, description=f"扫描完成，发现 {len(models)} 个模型")
        except Exception as e:
            print_error(f"扫描模型失败: {e}")
            raise typer.Exit(code=1)

    if not models:
        print_warning(f"在 {config.models_path} 中没有发现 SQLModel 模型")
        return

    print_success(f"发现 {len(models)} 个模型:")
    for model in models:
        console.print(f"  - {model.name}")

    # 检测变更
    if not force:
        print_info("检测模型变更...")
        changes = detector.detect_changes(models)

        if changes:
            console.print()
            console.print(detector.get_summary(changes))
            console.print()
        else:
            print_info("没有检测到变更")

        # 如果没有变更且不是强制模式，询问是否继续
        if not changes and not dry_run:
            print_info("模型没有变更，使用 --force 强制重新生成")
            return

    # 生成代码
    print_info("生成代码中...")
    generated_files = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("生成代码...", total=len(models))

        try:
            # 一次性生成所有代码（包括数据层基础设施文件）
            generated_files = generator.generate(models)
            progress.update(task, completed=len(models))
        except Exception as e:
            print_error(f"生成代码失败: {e}")

    # 写入文件或预览
    if dry_run:
        console.print()
        console.print(
            Panel(
                "[bold yellow]预览模式 - 以下文件将被生成:[/bold yellow]",
                border_style="yellow",
            )
        )

        for file in generated_files:
            console.print(f"  [cyan]{file.file_path}[/cyan]")
            console.print(f"    模型: {file.model_name}, 类型: {file.generator_type}")
    else:
        print_info("写入文件中...")

        try:
            generator.write_files(generated_files, dry_run=False)
            print_success(f"成功生成 {len(generated_files)} 个文件")
        except Exception as e:
            print_error(f"写入文件失败: {e}")
            raise typer.Exit(code=1)

        # 保存快照
        detector.save_snapshot(models)
        print_success("保存模型快照")

    # 显示摘要
    _display_summary(models, generated_files, dry_run)


def _display_summary(
    models: List,
    generated_files: List,
    dry_run: bool,
) -> None:
    """
    显示生成摘要

    Args:
        models: 模型列表
        generated_files: 生成的文件列表
        dry_run: 是否为预览模式
    """
    console.print()

    # 检查是否有数据层基础设施文件
    data_layer_files = [f for f in generated_files if f.generator_type == "data_layer"]
    model_files_list = [f for f in generated_files if f.generator_type != "data_layer"]

    # 如果有数据层文件，先显示
    if data_layer_files:
        console.print("[bold cyan]数据层基础设施文件:[/bold cyan]")
        for file in data_layer_files:
            console.print(f"  [green]✓[/green] {file.file_path}")
        console.print()

    # 创建摘要表格
    table = Table(title="生成摘要")
    table.add_column("模型", style="cyan")
    table.add_column("CRUD", style="green")
    table.add_column("Schemas", style="green")

    # 按模型分组统计
    model_files = {}
    for file in model_files_list:
        model_name = file.model_name or "Unknown"
        if model_name not in model_files:
            model_files[model_name] = {"crud": "-", "schemas": "-"}
        model_files[model_name][file.generator_type] = "✓"

    for model_name, files in model_files.items():
        table.add_row(
            model_name,
            files.get("crud", "-"),
            files.get("schemas", "-"),
        )

    console.print(table)

    # 显示统计信息
    mode_text = "[预览模式]" if dry_run else "[实际生成]"
    data_layer_text = (
        f"数据层文件: {len(data_layer_files)}\n" if data_layer_files else ""
    )
    console.print(
        Panel(
            f"{mode_text}\n"
            f"{data_layer_text}"
            f"模型数量: {len(models)}\n"
            f"文件数量: {len(generated_files)}",
            title="生成完成",
            border_style="yellow" if dry_run else "green",
        )
    )


@app.command(name="version")
def version_cmd() -> None:
    """
    显示版本信息

    示例:
        $ sqlmodel-crud version
        $ sqlmodel-crud --version
    """
    console.print(f"SQLModel CRUD Generator [cyan]v{__version__}[/cyan]")


def _version_callback(value: bool) -> None:
    """
    版本回调函数

    Args:
        value: 是否显示版本
    """
    if value:
        console.print(f"SQLModel CRUD Generator [cyan]v{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="显示版本信息",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    """
    SQLModel CRUD 代码生成器

    提供命令行接口用于初始化项目和生成 CRUD 代码。
    """
    pass


def main() -> None:
    """
    CLI 入口函数

    运行 Typer 应用程序
    """
    app()


if __name__ == "__main__":
    main()
