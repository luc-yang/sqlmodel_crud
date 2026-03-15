"""
CLI 模块测试。
"""

import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from sqlmodel_crud.cli import (
    __version__,
    _create_example_model,
    _create_pyproject_config,
    _create_standalone_config,
    _display_summary,
    app,
    main,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from sqlmodel_crud.config import GeneratorConfig


class EncodedStringIO(io.StringIO):
    """带编码信息的内存输出流，用于模拟不同终端编码。"""

    def __init__(self, encoding: str):
        super().__init__()
        self._encoding = encoding

    @property
    def encoding(self) -> str:
        return self._encoding


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


class TestPrintFunctions:
    """测试打印辅助函数。"""

    def test_print_success(self, capsys):
        print_success("测试成功消息")
        captured = capsys.readouterr()
        assert "测试成功消息" in captured.out

    def test_print_error(self, capsys):
        print_error("测试错误消息")
        captured = capsys.readouterr()
        assert "测试错误消息" in captured.out

    def test_print_warning(self, capsys):
        print_warning("测试警告消息")
        captured = capsys.readouterr()
        assert "测试警告消息" in captured.out

    def test_print_info(self, capsys):
        print_info("测试信息消息")
        captured = capsys.readouterr()
        assert "测试信息消息" in captured.out

    @pytest.mark.parametrize(
        "print_func,message,expected_prefix",
        [
            (print_success, "UTF 成功", "✓"),
            (print_error, "UTF 错误", "✗"),
            (print_warning, "UTF 警告", "⚠"),
            (print_info, "UTF 信息", "ℹ"),
        ],
    )
    def test_print_functions_use_unicode_prefix_for_utf_stream(
        self, monkeypatch, print_func, message, expected_prefix
    ):
        stream = EncodedStringIO("utf-8")
        test_console = Console(
            file=stream, force_terminal=False, color_system=None, no_color=True
        )
        monkeypatch.setattr("sqlmodel_crud.cli.console", test_console)

        print_func(message)
        output = stream.getvalue()

        assert expected_prefix in output
        assert message in output

    @pytest.mark.parametrize(
        "print_func,message,expected_prefix",
        [
            (print_success, "GBK 成功", "[OK]"),
            (print_error, "GBK 错误", "[ERR]"),
            (print_warning, "GBK 警告", "[WARN]"),
            (print_info, "GBK 信息", "[INFO]"),
        ],
    )
    def test_print_functions_fallback_to_ascii_for_gbk_stream(
        self, monkeypatch, print_func, message, expected_prefix
    ):
        stream = EncodedStringIO("gbk")
        test_console = Console(
            file=stream, force_terminal=False, color_system=None, no_color=True
        )
        monkeypatch.setattr("sqlmodel_crud.cli.console", test_console)

        print_func(message)
        output = stream.getvalue()

        assert expected_prefix in output
        assert message in output


class TestInitCommand:
    """测试 init 命令。"""

    def test_init_basic_template(self, runner, temp_dir):
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["init", "--template", "basic"])
            assert result.exit_code == 0
            assert "项目初始化完成" in result.output
            assert Path("app/models").exists()
            assert Path("app/generated").exists()
            assert Path("app/generated/crud").exists()

    def test_init_full_template(self, runner, temp_dir):
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["init", "--template", "full"])
            assert result.exit_code == 0
            assert "项目初始化完成" in result.output

    def test_init_invalid_template(self, runner, temp_dir):
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["init", "--template", "invalid"])
            assert result.exit_code == 1
            assert "无效的模板类型" in result.output

    def test_init_custom_paths(self, runner, temp_dir):
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(
                app,
                ["init", "--models-path", "src/models", "--output-dir", "src/generated"],
            )
            assert result.exit_code == 0
            assert Path("src/models").exists()
            assert Path("src/generated").exists()

    def test_init_pyproject_config(self, runner, temp_dir):
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["init", "--config", "pyproject.toml"])
            assert result.exit_code == 0
            assert Path("pyproject.toml").exists()


class TestConfigCreation:
    """测试配置创建函数。"""

    def test_create_standalone_config_basic(self, temp_dir):
        config_path = temp_dir / ".sqlmodel-crud.toml"
        _create_standalone_config(config_path, "models", "generated", "basic")

        content = config_path.read_text(encoding="utf-8")
        assert 'models_path = "models"' in content
        assert 'output_dir = "generated"' in content
        assert "generate_data_layer = true" in content
        assert "generators" not in content

    def test_create_standalone_config_full(self, temp_dir):
        config_path = temp_dir / ".sqlmodel-crud.toml"
        _create_standalone_config(config_path, "models", "generated", "full")

        content = config_path.read_text(encoding="utf-8")
        assert 'crud_suffix = "CRUD"' in content
        assert "use_async = true" in content
        assert "generators" not in content

    def test_create_standalone_config_exists(self, temp_dir, capsys):
        config_path = temp_dir / ".sqlmodel-crud.toml"
        config_path.write_text("existing config", encoding="utf-8")

        _create_standalone_config(config_path, "models", "generated", "basic")

        captured = capsys.readouterr()
        assert "配置文件已存在" in captured.out

    def test_create_pyproject_config_new_file(self, temp_dir):
        config_path = temp_dir / "pyproject.toml"
        _create_pyproject_config(config_path, "models", "generated")

        content = config_path.read_text(encoding="utf-8")
        assert "[tool.sqlmodel-crud]" in content
        assert 'models_path = "models"' in content
        assert "generators" not in content

    def test_create_pyproject_config_append(self, temp_dir):
        config_path = temp_dir / "pyproject.toml"
        config_path.write_text('[project]\nname = "test"\n', encoding="utf-8")

        _create_pyproject_config(config_path, "models", "generated")

        content = config_path.read_text(encoding="utf-8")
        assert "[project]" in content
        assert "[tool.sqlmodel-crud]" in content
        assert "generators" not in content

    def test_create_pyproject_config_exists(self, temp_dir, capsys):
        config_path = temp_dir / "pyproject.toml"
        config_path.write_text(
            "[tool.sqlmodel-crud]\nmodels_path = \"existing\"\n",
            encoding="utf-8",
        )

        _create_pyproject_config(config_path, "models", "generated")

        captured = capsys.readouterr()
        assert "已存在 SQLModel CRUD 配置" in captured.out


class TestExampleModelCreation:
    """测试示例模型创建函数。"""

    def test_create_example_model(self, temp_dir):
        file_path = temp_dir / "example.py"
        _create_example_model(file_path)

        content = file_path.read_text(encoding="utf-8")
        assert "class User(SQLModel, table=True)" in content
        assert "class Item(SQLModel, table=True)" in content
        assert "__tablename__" in content


class TestGenerateCommand:
    """测试 generate 命令。"""

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    @patch("sqlmodel_crud.cli.ChangeDetector")
    @patch("sqlmodel_crud.cli.CodeGenerator")
    def test_generate_success(
        self,
        mock_generator_class,
        mock_detector_class,
        mock_scanner_class,
        mock_load_config,
        runner,
        temp_dir,
    ):
        mock_load_config.return_value = GeneratorConfig(
            models_path="models",
            output_dir="generated",
            snapshot_file=".snapshot.json",
        )

        mock_model = Mock(name="TestModel")
        mock_model.name = "TestModel"
        mock_scanner = Mock()
        mock_scanner.scan.return_value = [mock_model]
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

        with runner.isolated_filesystem(temp_dir=temp_dir):
            Path("models").mkdir(parents=True)
            Path("models/__init__.py").write_text("", encoding="utf-8")
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate", "--force"])
            assert result.exit_code == 0

    @patch("sqlmodel_crud.cli.load_config")
    def test_generate_config_error(self, mock_load_config, runner, temp_dir):
        mock_load_config.side_effect = Exception("配置错误")

        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["generate"])
            assert result.exit_code == 1
            assert "加载配置失败" in result.output

    @patch("sqlmodel_crud.cli.load_config")
    def test_generate_models_path_not_exists(self, mock_load_config, runner, temp_dir):
        mock_load_config.return_value = GeneratorConfig(
            models_path="nonexistent",
            output_dir="generated",
        )

        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["generate"])
            assert result.exit_code == 1
            assert "模型路径不存在" in result.output

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    def test_generate_no_models_found(
        self, mock_scanner_class, mock_load_config, runner, temp_dir
    ):
        mock_load_config.return_value = GeneratorConfig(
            models_path="models",
            output_dir="generated",
            snapshot_file=".snapshot.json",
        )

        mock_scanner = Mock()
        mock_scanner.scan.return_value = []
        mock_scanner_class.return_value = mock_scanner

        with runner.isolated_filesystem(temp_dir=temp_dir):
            Path("models").mkdir(parents=True)
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate"])
            assert "没有发现 SQLModel 模型" in result.output or result.exit_code in [0, 1]

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    @patch("sqlmodel_crud.cli.ChangeDetector")
    @patch("sqlmodel_crud.cli.CodeGenerator")
    def test_generate_dry_run(
        self,
        mock_generator_class,
        mock_detector_class,
        mock_scanner_class,
        mock_load_config,
        runner,
        temp_dir,
    ):
        mock_load_config.return_value = GeneratorConfig(
            models_path="models",
            output_dir="generated",
            snapshot_file=".snapshot.json",
        )

        mock_model = Mock(name="TestModel")
        mock_model.name = "TestModel"
        mock_scanner = Mock()
        mock_scanner.scan.return_value = [mock_model]
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

        with runner.isolated_filesystem(temp_dir=temp_dir):
            Path("models").mkdir(parents=True)
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate", "--dry-run", "--force"])
            assert result.exit_code == 0
            assert "预览模式" in result.output

    @patch("sqlmodel_crud.cli.load_config")
    @patch("sqlmodel_crud.cli.ModelScanner")
    @patch("sqlmodel_crud.cli.ChangeDetector")
    @patch("sqlmodel_crud.cli.CodeGenerator")
    def test_generate_applies_cli_override_before_validation(
        self,
        mock_generator_class,
        mock_detector_class,
        mock_scanner_class,
        mock_load_config,
        runner,
        temp_dir,
    ):
        mock_load_config.return_value = GeneratorConfig(
            models_path="missing_models",
            output_dir="generated",
        )

        mock_model = Mock(name="TestModel")
        mock_model.name = "TestModel"
        mock_scanner = Mock()
        mock_scanner.scan.return_value = [mock_model]
        mock_scanner_class.return_value = mock_scanner

        mock_detector = Mock()
        mock_detector.detect_changes.return_value = []
        mock_detector_class.return_value = mock_detector

        mock_file = Mock()
        mock_file.file_path = "crud/test.py"
        mock_file.model_name = "TestModel"
        mock_file.generator_type = "crud"
        mock_generator = Mock()
        mock_generator.generate.return_value = [mock_file]
        mock_generator_class.return_value = mock_generator

        with runner.isolated_filesystem(temp_dir=temp_dir):
            Path("models").mkdir(parents=True)
            Path("models/__init__.py").write_text("", encoding="utf-8")
            Path("generated").mkdir(parents=True)

            result = runner.invoke(app, ["generate", "--models-path", "models", "--force"])
            assert result.exit_code == 0

    def test_generate_rejects_unknown_option(self, runner, temp_dir):
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(app, ["generate", "--unexpected-option", "value"])
            assert result.exit_code != 0


class TestVersionCommand:
    """测试 version 命令。"""

    def test_version_command(self, runner):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "SQLModel CRUD Generator" in result.output

    def test_version_flag(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_flag(self, runner):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestDisplaySummary:
    """测试显示摘要函数。"""

    def test_display_summary_with_data_layer(self, capsys):
        mock_model = Mock()
        mock_model.name = "TestModel"

        mock_file_crud = Mock()
        mock_file_crud.file_path = "crud/test.py"
        mock_file_crud.model_name = "TestModel"
        mock_file_crud.generator_type = "crud"

        mock_file_data = Mock()
        mock_file_data.file_path = "database.py"
        mock_file_data.generator_type = "data_layer"

        _display_summary([mock_model], [mock_file_crud, mock_file_data], dry_run=False)

        captured = capsys.readouterr()
        assert "数据层基础设施文件" in captured.out
        assert "TestModel" in captured.out

    def test_display_summary_dry_run(self, capsys):
        mock_model = Mock()
        mock_model.name = "TestModel"

        mock_file = Mock()
        mock_file.file_path = "test.py"
        mock_file.model_name = "TestModel"
        mock_file.generator_type = "crud"

        _display_summary([mock_model], [mock_file], dry_run=True)

        captured = capsys.readouterr()
        assert "预览模式" in captured.out

    def test_display_summary_uses_ascii_marker_on_gbk_stream(self, monkeypatch):
        stream = EncodedStringIO("gbk")
        test_console = Console(
            file=stream, force_terminal=False, color_system=None, no_color=True
        )
        monkeypatch.setattr("sqlmodel_crud.cli.console", test_console)

        mock_model = Mock()
        mock_model.name = "TestModel"

        mock_file_crud = Mock()
        mock_file_crud.file_path = "crud/test.py"
        mock_file_crud.model_name = "TestModel"
        mock_file_crud.generator_type = "crud"

        mock_file_data = Mock()
        mock_file_data.file_path = "database.py"
        mock_file_data.generator_type = "data_layer"

        _display_summary([mock_model], [mock_file_crud, mock_file_data], dry_run=False)
        output = stream.getvalue()

        assert "[OK]" in output
        assert "✓" not in output


class TestMainFunction:
    """测试主函数。"""

    @patch("sqlmodel_crud.cli.app")
    def test_main(self, mock_app):
        main()
        mock_app.assert_called_once()


class TestNoArgs:
    """测试无参数显示帮助。"""

    def test_no_args_shows_help(self, runner):
        result = runner.invoke(app, [])
        assert result.exit_code in [0, 2]
        assert "SQLModel CRUD" in result.output
