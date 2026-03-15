"""
配置管理模块测试。

测试 GeneratorConfig 类和配置加载函数的功能。
"""

from pathlib import Path

import pytest

from sqlmodel_crud.config import GeneratorConfig, load_config, load_config_from_file


class TestGeneratorConfig:
    """测试 GeneratorConfig 类。"""

    def test_default_values(self):
        """测试默认值。"""
        config = GeneratorConfig()
        assert config.models_path == "app/models"
        assert config.output_dir == "app/generated"
        assert config.template_dir is None
        assert config.crud_suffix == "CRUD"
        assert config.type_mapping == {}
        assert config.exclude_models == []
        assert config.snapshot_file == ".sqlmodel-crud-snapshot.json"

    def test_custom_values(self):
        """测试自定义值。"""
        config = GeneratorConfig(
            models_path=".",
            output_dir="custom/output",
            template_dir=None,
            crud_suffix="Manager",
            type_mapping={"datetime": "str"},
            exclude_models=["BaseModel"],
            snapshot_file="custom-snapshot.json",
        )
        assert config.output_dir == "custom/output"
        assert config.crud_suffix == "Manager"
        assert config.type_mapping == {"datetime": "str"}
        assert config.exclude_models == ["BaseModel"]
        assert config.snapshot_file == "custom-snapshot.json"

    @pytest.mark.parametrize("unknown_field", ["unexpected_option", "extra_suffix"])
    def test_rejects_unknown_fields(self, unknown_field):
        """测试未知配置字段会被明确拒绝。"""
        with pytest.raises(Exception, match=unknown_field):
            GeneratorConfig(**{unknown_field: "value"})

    def test_validate_models_path_is_file(self, tmp_path):
        """测试模型路径是文件而非目录的验证。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('ok')\n", encoding="utf-8")
        config = GeneratorConfig(models_path=str(test_file))
        config.validate_all()

    def test_validate_template_dir_is_file(self, tmp_path):
        """测试模板目录是文件而非目录的验证。"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test", encoding="utf-8")
        config = GeneratorConfig(
            models_path=".",
            template_dir=str(test_file),
        )
        with pytest.raises(ValueError, match="模板路径必须是目录"):
            config.validate_all()

    def test_validate_all_success(self, tmp_path):
        """测试完整验证成功。"""
        config = GeneratorConfig(
            models_path=str(tmp_path),
            output_dir="output",
        )
        config.validate_all()

    def test_validate_all_nonexistent_models_path(self):
        """测试完整验证 - 不存在的模型路径。"""
        config = GeneratorConfig(
            models_path="/nonexistent/path/12345",
        )
        with pytest.raises(ValueError, match="模型路径不存在"):
            config.validate_all()


class TestLoadConfigFromFile:
    """测试从文件加载配置。"""

    def test_load_from_toml_file(self, tmp_path):
        """测试从 TOML 文件加载配置。"""
        config_file = tmp_path / ".sqlmodel-crud.toml"
        config_file.write_text(
            """
[sqlmodel-crud]
models_path = "."
output_dir = "custom/output"
crud_suffix = "Manager"
""".strip(),
            encoding="utf-8",
        )

        config = load_config_from_file(str(config_file))
        assert config is not None
        assert config.output_dir == "custom/output"
        assert config.crud_suffix == "Manager"

    def test_load_from_nonexistent_file(self):
        """测试从不存在的文件加载配置。"""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/config.toml")

    def test_load_from_empty_file(self, tmp_path):
        """测试从空文件加载配置。"""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("", encoding="utf-8")

        config = load_config_from_file(str(config_file))
        assert config is None

    def test_load_config_with_unknown_field_should_raise(self, tmp_path):
        """未知配置字段应直接报错。"""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text(
            """
[sqlmodel-crud]
models_path = "."
unexpected_option = true
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="unexpected_option"):
            load_config_from_file(str(config_file))


class TestLoadConfig:
    """测试综合配置加载。"""

    def test_load_default_config(self, tmp_path, monkeypatch):
        """测试加载默认配置。"""
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert isinstance(config, GeneratorConfig)
        assert config.output_dir == "app/generated"

    def test_load_with_env_override(self, monkeypatch, tmp_path):
        """测试环境变量覆盖。"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SQLMODEL_CRUD_OUTPUT_DIR", "env/output")

        config = load_config()
        assert config.output_dir == "env/output"

    def test_load_with_custom_config_file(self, tmp_path):
        """测试从自定义配置文件加载。"""
        config_file = tmp_path / "custom.toml"
        config_file.write_text(
            """
[sqlmodel-crud]
models_path = "."
output_dir = "file/output"
""".strip(),
            encoding="utf-8",
        )

        config = load_config(config_path=str(config_file))
        assert config.output_dir == "file/output"

    def test_load_invalid_config_should_raise(self, tmp_path):
        """未知字段应抛错，不能静默忽略。"""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text(
            """
[sqlmodel-crud]
extra_suffix = "DTO"
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="extra_suffix"):
            load_config(config_path=str(config_file))
