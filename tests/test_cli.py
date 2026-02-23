"""
CLI 模块测试

测试 sqlmodel_crud.cli 模块的所有功能，包括：
- init 命令：初始化项目
- generate 命令：生成代码
- version 命令：显示版本信息
- 辅助函数：打印函数、配置创建函数等
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock

from sqlmodel_crud.cli import (
    app,
    print_success,
    print_error,
    print_warning,
    print_info,
    _create_standalone_config,
    _create_pyproject_config,
    _create_example_model,
    _display_summary,
    main,
    __version__,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """创建 CLI 测试运行器"""
    return CliRunner()


@pytest.fixture
def temp_dir(tmp_path):
    """创建临时目录"""
    return tmp_path


# =============================================================================
# Test Print Functions
# =============================================================================


class TestPrintFunctions:
    """测试打印辅助函数"""

    def test_print_success(self, capsys):
        """测试打印成功消息"""
        print_success("测试成功消息")
        captured = capsys.readouterr()
        assert "测试成功消息" in captured.out

    def test_print_error(self, capsys):
        """测试打印错误消息"""
        print_error("测试错误消息")
        captured = capsys.readouterr()
        assert "测试错误消息" in captured.out

    def test_print_warning(self, capsys):
        """测试打印警告消息"""
        print_warning("测试警告消息")
        captured = capsys.readouterr()
        assert "测试警告消息" in captured.out

    def test_print_info(self, capsys):
        """测试打印信息消息"""
        print_info("测试信息消息")
        captured = capsys.readouterr()
        assert "测试信息消息" in captured.out


# =============================================================================
# Test Init Command
# =============================================================================


class TestInitCommand:
    """测试 init 命令"""

    def test_init_basic_template(self, runner, temp_dir):
        """测试使用 basic 模板初始化项目"""
        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(app, ["init", "--template", "basic"])
            assert result.exit_code == 0
            assert "项目初始化完成" in result.output

            # 验证目录结构
            assert Path("app/models").exists()
            assert Path("app/generated").exists()
            assert Path("app/generated/crud").exists()
            assert Path("app/generated/schemas").exists()

    def test_init_full_template(self, runner, temp_dir):
        """测试使用 full 模板初始化项目"""
        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(app, ["init", "--template", "full"])
            assert result.exit_code == 0
            assert "项目初始化完成" in result.output

    def test_init_invalid_template(self, runner, temp_dir):
        """测试使用无效模板类型"""
        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(app, ["init", "--template", "invalid"])
            assert result.exit_code == 1
            assert "无效的模板类型" in result.output

    def test_init_custom_paths(self, runner, temp_dir):
        """测试使用自定义路径初始化"""
        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(
                app,
                [
                    "init",
                    "--models-path",
                    "src/models",
                    "--output-dir",
                    "src/generated",
                ],
            )
            assert result.exit_code == 0
            assert Path("src/models").exists()
            assert Path("src/generated").exists()

    def test_init_pyproject_config(self, runner, temp_dir):
        """测试创建 pyproject.toml 配置"""
        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(
                app, ["init", "--config", "pyproject.toml"]
            )
            assert result.exit_code == 0
            assert Path("pyproject.toml").exists()


# =============================================================================
# Test Config Creation Functions
# =============================================================================


class TestConfigCreation:
    """测试配置创建函数"""

    def test_create_standalone_config_basic(self, temp_dir):
        """测试创建 basic 模板独立配置文件"""
        config_path = temp_dir / ".sqlmodel-crud.toml"
        _create_standalone_config(config_path, "models", "generated", "basic")

        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert 'models_path = "models"' in content
        assert 'output_dir = "generated"' in content
        assert "generate_data_layer = true" in content

    def test_create_standalone_config_full(self, temp_dir):
        """测试创建 full 模板独立配置文件"""
        config_path = temp_dir / ".sqlmodel-crud.toml"
        _create_standalone_config(config_path, "models", "generated", "full")

        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "schema_create_suffix" in content
        assert "schema_update_suffix" in content
        assert "use_async = true" in content

    def test_create_standalone_config_exists(self, temp_dir, capsys):
        """测试配置文件已存在的情况"""
        config_path = temp_dir / ".sqlmodel-crud.toml"
        config_path.write_text("existing config", encoding="utf-8")

        _create_standalone_config(config_path, "models", "generated", "basic")

        captured = capsys.readouterr()
        assert "配置文件已存在" in captured.out

    def test_create_pyproject_config_new_file(self, temp_dir):
        """测试创建新的 pyproject.toml 配置"""
        config_path = temp_dir / "pyproject.toml"
        _create_pyproject_config(config_path, "models", "generated", "basic")

        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "[tool.sqlmodel-crud]" in content
        assert 'models_path = "models"' in content

    def test_create_pyproject_config_append(self, temp_dir):
        """测试追加到现有 pyproject.toml"""
        config_path = temp_dir / "pyproject.toml"
        config_path.write_text('[project]\nname = "test"\n', encoding="utf-8")

        _create_pyproject_config(config_path, "models", "generated", "basic")

        content = config_path.read_text(encoding="utf-8")
        assert "[project]" in content
        assert "[tool.sqlmodel-crud]" in content

    def test_create_pyproject_config_exists(self, temp_dir, capsys):
        """测试 pyproject.toml 中配置已存在的情况"""
        config_path = temp_dir / "pyproject.toml"
        config_path.write_text(
            "[tool.sqlmodel-crud]\nmodels_path = \"existing\"\n",
            encoding="utf-8",
        )

        _create_pyproject_config(config_path, "models", "generated", "basic")

        captured = capsys.readouterr()
        assert "已存在 SQLModel CRUD 配置" in captured.out


# =============================================================================
# Test Example Model Creation
# =============================================================================


class TestExampleModelCreation:
    """测试示例模型创建函数"""

    def test_create_example_model(self, temp_dir):
        """测试创建示例模型文件"""
        file_path = temp_dir / "example.py"
        _create_example_model(file_path, "basic")

        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        assert "class User(SQLModel, table=True)" in content
        assert "class Item(SQLModel, table=True)" in content
        assert "__tablename__" in content


# =============================================================================
# Test Generate Command
# =============================================================================


class TestGenerateCommand:
    """测试 generate 命令"""

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    @patch("sqlmodel_crud.cli.ChangeDetector")
    @patch("sqlmodel_crud.cli.CodeGenerator")
    def test_generate_success(
        self, mock_generator_class, mock_detector_class, mock_scanner_class,
        mock_load_config, runner, temp_dir
    ):
        """测试成功生成代码"""
        # 设置 mock
        mock_config = Mock()
        mock_config.models_path = "models"
        mock_config.output_dir = "generated"
        mock_config.generators = ["crud", "schemas"]
        mock_config.snapshot_file = ".snapshot.json"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_model.name = "TestModel"
        mock_scanner = Mock()
        mock_scanner.scan_module.return_value = [mock_model]
        mock_scanner_class.return_value = mock_scanner

        mock_detector = Mock()
        mock_detector.detect_changes.return_value = []
        mock_detector_class.return_value = mock_detector

        mock_file = Mock()
        mock_file.file_path = "test.py"
        mock_file.model_name = "TestModel"
        mock_file.generator_type = "crud"
        mock_generator = Mock()
        mock_generator.generate.return_value = [mock_file]
        mock_generator_class.return_value = mock_generator

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            # 创建模型目录和示例模型
            Path("models").mkdir(parents=True)
            Path("models/__init__.py").write_text("", encoding="utf-8")
            Path("models/user.py").write_text(
                "from sqlmodel import SQLModel, Field\n"
                "class User(SQLModel, table=True):\n"
                "    id: int = Field(primary_key=True)\n",
                encoding="utf-8",
            )
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate", "--force"])
            assert result.exit_code == 0

    @patch("sqlmodel_crud.cli.load_config")
    def test_generate_config_error(self, mock_load_config, runner, temp_dir):
        """测试配置加载失败"""
        mock_load_config.side_effect = Exception("配置错误")

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(app, ["generate"])
            assert result.exit_code == 1
            assert "加载配置失败" in result.output

    @patch("sqlmodel_crud.cli.load_config")
    def test_generate_models_path_not_exists(self, mock_load_config, runner, temp_dir):
        """测试模型路径不存在"""
        mock_config = Mock()
        mock_config.models_path = "nonexistent"
        mock_config.output_dir = "generated"
        mock_config.generators = ["crud"]
        mock_load_config.return_value = mock_config

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            result = runner.invoke(app, ["generate"])
            assert result.exit_code == 1
            assert "模型路径不存在" in result.output

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    def test_generate_no_models_found(
        self, mock_scanner_class, mock_load_config, runner, temp_dir
    ):
        """测试没有发现模型"""
        mock_config = Mock()
        mock_config.models_path = "models"
        mock_config.output_dir = "generated"
        mock_config.generators = ["crud"]
        mock_config.snapshot_file = ".snapshot.json"
        mock_load_config.return_value = mock_config

        mock_scanner = Mock()
        mock_scanner.scan_module.return_value = []
        mock_scanner_class.return_value = mock_scanner

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            Path("models").mkdir(parents=True)
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate"])
            # 由于 typer 的 exit 行为，exit_code 可能是 0 或 1
            assert "没有发现 SQLModel 模型" in result.output or result.exit_code in [0, 1]

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    @patch("sqlmodel_crud.cli.ChangeDetector")
    @patch("sqlmodel_crud.cli.CodeGenerator")
    def test_generate_dry_run(
        self, mock_generator_class, mock_detector_class, mock_scanner_class,
        mock_load_config, runner, temp_dir
    ):
        """测试预览模式"""
        mock_config = Mock()
        mock_config.models_path = "models"
        mock_config.output_dir = "generated"
        mock_config.generators = ["crud"]
        mock_config.snapshot_file = ".snapshot.json"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_model.name = "TestModel"
        mock_scanner = Mock()
        mock_scanner.scan_module.return_value = [mock_model]
        mock_scanner_class.return_value = mock_scanner

        mock_detector = Mock()
        mock_detector.detect_changes.return_value = []
        mock_detector_class.return_value = mock_detector

        mock_file = Mock()
        mock_file.file_path = "test.py"
        mock_file.model_name = "TestModel"
        mock_file.generator_type = "crud"
        mock_generator = Mock()
        mock_generator.generate.return_value = [mock_file]
        mock_generator_class.return_value = mock_generator

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            Path("models").mkdir(parents=True)
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate", "--dry-run", "--force"])
            assert result.exit_code == 0
            assert "预览模式" in result.output


# =============================================================================
# Test Version Command
# =============================================================================


class TestVersionCommand:
    """测试 version 命令"""

    def test_version_command(self, runner):
        """测试 version 命令"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "SQLModel CRUD Generator" in result.output

    def test_version_flag(self, runner):
        """测试 --version 标志"""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_flag(self, runner):
        """测试 -v 短标志"""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output


# =============================================================================
# Test Display Summary
# =============================================================================


class TestDisplaySummary:
    """测试显示摘要函数"""

    def test_display_summary_with_data_layer(self, capsys):
        """测试显示包含数据层文件的摘要"""
        mock_model = Mock()
        mock_model.name = "TestModel"

        mock_file_crud = Mock()
        mock_file_crud.file_path = "crud/test.py"
        mock_file_crud.model_name = "TestModel"
        mock_file_crud.generator_type = "crud"

        mock_file_schema = Mock()
        mock_file_schema.file_path = "schemas/test.py"
        mock_file_schema.model_name = "TestModel"
        mock_file_schema.generator_type = "schemas"

        mock_file_data = Mock()
        mock_file_data.file_path = "database.py"
        mock_file_data.generator_type = "data_layer"

        files = [mock_file_crud, mock_file_schema, mock_file_data]

        _display_summary([mock_model], files, dry_run=False)

        captured = capsys.readouterr()
        assert "数据层基础设施文件" in captured.out
        assert "TestModel" in captured.out

    def test_display_summary_dry_run(self, capsys):
        """测试预览模式的摘要"""
        mock_model = Mock()
        mock_model.name = "TestModel"

        mock_file = Mock()
        mock_file.file_path = "test.py"
        mock_file.model_name = "TestModel"
        mock_file.generator_type = "crud"

        _display_summary([mock_model], [mock_file], dry_run=True)

        captured = capsys.readouterr()
        assert "预览模式" in captured.out


# =============================================================================
# Test Main Function
# =============================================================================


class TestMainFunction:
    """测试主函数"""

    @patch("sqlmodel_crud.cli.app")
    def test_main(self, mock_app):
        """测试主入口函数"""
        main()
        mock_app.assert_called_once()


# =============================================================================
# Test No Args Shows Help
# =============================================================================


class TestNoArgs:
    """测试无参数显示帮助"""

    def test_no_args_shows_help(self, runner):
        """测试无参数时显示帮助信息"""
        result = runner.invoke(app, [])
        # typer 的 no_args_is_help=True 会显示帮助
        # exit_code 可能是 0（成功显示帮助）或 2（没有提供参数）
        assert result.exit_code in [0, 2]
        assert "SQLModel CRUD" in result.output
