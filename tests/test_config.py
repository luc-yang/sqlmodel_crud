"""
配置管理模块测试

测试 GeneratorConfig 类和配置加载函数的功能。
"""

from pathlib import Path

import pytest

from sqlmodel_crud.config import (
    GeneratorConfig,
    DEFAULT_CONFIG,
    load_config,
    load_config_from_file,
    VALID_GENERATORS,
)


class TestGeneratorConfig:
    """测试 GeneratorConfig 类"""

    def test_default_values(self):
        """测试默认值"""
        config = GeneratorConfig()
        assert config.models_path == "app/models"
        assert config.output_dir == "app/generated"
        assert config.generators == ["crud", "schemas"]
        assert config.template_dir is None
        assert config.crud_suffix == "CRUD"
        assert config.schema_suffix == "Schema"
        assert config.type_mapping == {}
        assert config.exclude_models == []
        assert config.snapshot_file == ".sqlmodel-crud-snapshot.json"

    def test_custom_values(self):
        """测试自定义值"""
        config = GeneratorConfig(
            models_path=".",
            output_dir="custom/output",
            generators=["crud"],
            template_dir=None,
            crud_suffix="Manager",
            schema_suffix="DTO",
            type_mapping={"datetime": "str"},
            exclude_models=["BaseModel"],
            snapshot_file="custom-snapshot.json",
        )
        assert config.output_dir == "custom/output"
        assert config.generators == ["crud"]
        assert config.crud_suffix == "Manager"
        assert config.schema_suffix == "DTO"
        assert config.type_mapping == {"datetime": "str"}
        assert config.exclude_models == ["BaseModel"]
        assert config.snapshot_file == "custom-snapshot.json"

    def test_validate_generators_valid(self):
        """测试合法的生成器类型验证"""
        config = GeneratorConfig(
            models_path=".",
            generators=["crud", "schemas"],
        )
        assert config.generators == ["crud", "schemas"]

    def test_validate_generators_all(self):
        """测试 'all' 生成器类型"""
        config = GeneratorConfig(
            models_path=".",
            generators=["all"],
        )
        assert config.generators == ["crud", "schemas"]

    def test_validate_generators_invalid(self):
        """测试非法的生成器类型验证"""
        with pytest.raises(ValueError, match="非法的生成器类型"):
            GeneratorConfig(
                models_path=".",
                generators=["invalid"],
            )

    def test_validate_models_path_is_file(self, tmp_path):
        """测试模型路径是文件而非目录的验证"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with pytest.raises(ValueError, match="模型路径必须是目录"):
            GeneratorConfig(
                models_path=str(test_file),
            )

    def test_validate_template_dir_is_file(self, tmp_path):
        """测试模板目录是文件而非目录的验证"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with pytest.raises(ValueError, match="模板路径必须是目录"):
            GeneratorConfig(
                models_path=".",
                template_dir=str(test_file),
            )

    def test_validate_all_success(self, tmp_path):
        """测试完整验证成功"""
        config = GeneratorConfig(
            models_path=str(tmp_path),
            output_dir="output",
            generators=["crud", "schemas"],
        )
        config.validate_all()  # 不应抛出异常

    def test_validate_all_nonexistent_models_path(self):
        """测试完整验证 - 不存在的模型路径"""
        config = GeneratorConfig(
            models_path="/nonexistent/path/12345",
        )
        with pytest.raises(ValueError, match="模型路径不存在"):
            config.validate_all()


class TestLoadConfigFromFile:
    """测试从文件加载配置"""

    def test_load_from_toml_file(self, tmp_path):
        """测试从 TOML 文件加载配置"""
        config_file = tmp_path / ".sqlmodel-crud.toml"
        config_file.write_text("""
[sqlmodel-crud]
models_path = "."
output_dir = "custom/output"
generators = ["crud", "schemas"]
crud_suffix = "Manager"
""")

        config = load_config_from_file(str(config_file))
        assert config is not None
        assert config.output_dir == "custom/output"
        assert config.generators == ["crud", "schemas"]
        assert config.crud_suffix == "Manager"

    def test_load_from_nonexistent_file(self):
        """测试从不存在的文件加载配置"""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/config.toml")

    def test_load_from_empty_file(self, tmp_path):
        """测试从空文件加载配置"""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")

        config = load_config_from_file(str(config_file))
        assert config is None


class TestLoadConfig:
    """测试综合配置加载"""

    def test_load_default_config(self):
        """测试加载默认配置"""
        config = load_config()
        assert isinstance(config, GeneratorConfig)
        assert config.output_dir == DEFAULT_CONFIG.output_dir

    def test_load_with_env_override(self, monkeypatch):
        """测试环境变量覆盖"""
        monkeypatch.setenv("SQLMODEL_CRUD_OUTPUT_DIR", "env/output")
        monkeypatch.setenv("SQLMODEL_CRUD_GENERATORS", "crud,schemas")

        config = load_config()
        assert config.output_dir == "env/output"
        assert config.generators == ["crud", "schemas"]

        # 环境变量由 monkeypatch 自动清理

    def test_load_with_custom_config_file(self, tmp_path, monkeypatch):
        """测试从自定义配置文件加载"""
        config_file = tmp_path / "custom.toml"
        config_file.write_text("""
[sqlmodel-crud]
models_path = "."
output_dir = "file/output"
generators = ["schemas"]
""")

        config = load_config(config_path=str(config_file))
        assert config.output_dir == "file/output"
        assert config.generators == ["schemas"]


class TestValidGenerators:
    """测试合法生成器类型常量"""

    def test_valid_generators_set(self):
        """测试合法生成器类型集合"""
        assert "crud" in VALID_GENERATORS
        assert "schemas" in VALID_GENERATORS
        assert "all" in VALID_GENERATORS
