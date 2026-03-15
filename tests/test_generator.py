"""
代码生成器模块测试。
"""

from contextlib import redirect_stdout
from datetime import datetime
import io
from pathlib import Path
from typing import List, Optional

import pytest

import sqlmodel_crud.generator as generator_module
from sqlmodel_crud.config import GeneratorConfig
from sqlmodel_crud.exceptions import ValidationError
from sqlmodel_crud.generator import CodeGenerator, GeneratedFile, generate
from sqlmodel_crud.scanner import FieldMeta, FieldType, ModelMeta


class EncodedStringIO(io.StringIO):
    """带编码信息的内存输出流，用于模拟不同终端编码。"""

    def __init__(self, encoding: str):
        super().__init__()
        self._encoding = encoding

    @property
    def encoding(self) -> str:
        return self._encoding


@pytest.fixture
def generator_config(tmp_path):
    """创建生成器配置 fixture。"""
    return GeneratorConfig(
        models_path=str(tmp_path / "models"),
        output_dir=str(tmp_path / "generated"),
        crud_suffix="CRUD",
    )


@pytest.fixture
def code_generator(generator_config):
    """创建代码生成器 fixture。"""
    return CodeGenerator(generator_config)


@pytest.fixture
def sample_model():
    """创建示例模型元数据 fixture。"""
    id_field = FieldMeta(
        name="id",
        field_type=FieldType.INTEGER,
        python_type=int,
        primary_key=True,
        nullable=False,
    )
    name_field = FieldMeta(
        name="name",
        field_type=FieldType.STRING,
        python_type=str,
        nullable=False,
    )
    return ModelMeta(
        name="User",
        table_name="users",
        fields=[id_field, name_field],
    )


class TestGeneratedFile:
    """测试 GeneratedFile 数据类。"""

    def test_generated_file_creation(self):
        file = GeneratedFile(
            file_path="test.py",
            content="print('hello')",
            model_name="TestModel",
            generator_type="crud",
        )
        assert file.file_path == "test.py"
        assert file.content == "print('hello')"
        assert file.model_name == "TestModel"
        assert file.generator_type == "crud"

    def test_generated_file_optional_fields(self):
        file = GeneratedFile(file_path="test.py", content="content")
        assert file.model_name is None
        assert file.generator_type == ""


class TestCodeGeneratorInit:
    """测试 CodeGenerator 初始化。"""

    def test_init_with_config(self, generator_config):
        generator = CodeGenerator(generator_config)
        assert generator.config == generator_config
        assert generator.generated_files == []
        assert generator.jinja_env is not None

    def test_init_sets_up_jinja_env(self, generator_config):
        generator = CodeGenerator(generator_config)
        assert "snake_case" in generator.jinja_env.filters
        assert "pascal_case" in generator.jinja_env.filters
        assert "camel_case" in generator.jinja_env.filters

    def test_module_exports_code_generator(self):
        assert hasattr(generator_module, "CodeGenerator")


class TestHelperMethods:
    """测试辅助方法。"""

    def test_to_snake_case(self, code_generator):
        assert code_generator._to_snake_case("User") == "user"
        assert code_generator._to_snake_case("UserProfile") == "user_profile"
        assert code_generator._to_snake_case("APIKey") == "api_key"

    def test_to_pascal_case(self, code_generator):
        assert code_generator._to_pascal_case("user") == "User"
        assert code_generator._to_pascal_case("user_profile") == "UserProfile"

    def test_to_camel_case(self, code_generator):
        assert code_generator._to_camel_case("user") == "user"
        assert code_generator._to_camel_case("user_profile") == "userProfile"

    def test_get_primary_key_field(self, code_generator, sample_model):
        pk_field = code_generator._get_primary_key_field(sample_model)
        assert pk_field is not None
        assert pk_field.name == "id"

    def test_get_primary_key_field_falls_back_to_id(self, code_generator):
        id_field = FieldMeta(name="id", field_type=FieldType.INTEGER, python_type=int)
        model = ModelMeta(name="Test", fields=[id_field])
        assert code_generator._get_primary_key_field(model) is id_field

    def test_get_primary_key_field_none(self, code_generator):
        name_field = FieldMeta(
            name="name", field_type=FieldType.STRING, python_type=str
        )
        model = ModelMeta(name="Test", fields=[name_field])
        assert code_generator._get_primary_key_field(model) is None

    def test_format_type_basic(self, code_generator):
        assert code_generator._format_type(str) == "str"
        assert code_generator._format_type(int) == "int"
        assert code_generator._format_type(float) == "float"
        assert code_generator._format_type(bool) == "bool"

    def test_format_type_optional(self, code_generator):
        result = code_generator._format_type(Optional[int])
        assert result == "Optional[int]"

    def test_format_type_list(self, code_generator):
        assert code_generator._format_type(List[str]) == "List[str]"

    def test_format_type_none(self, code_generator):
        assert code_generator._format_type(None) == "Any"

    def test_get_type_import_datetime(self, code_generator):
        result = code_generator._get_type_import(datetime)
        assert "datetime import datetime" in result

    def test_get_output_path_crud(self, code_generator):
        assert code_generator._get_output_path("crud", "User") == Path("crud/user.py")

    def test_get_output_path_invalid_generator(self, code_generator):
        with pytest.raises(ValueError):
            code_generator._get_output_path("invalid", "UserProfile")

    def test_generate_file_header(self, code_generator):
        header = code_generator._generate_file_header("User", "CRUD")
        assert "User" in header
        assert "CRUD" in header


class TestGenerateMethods:
    """测试生成方法。"""

    def test_generate_crud(self, code_generator, sample_model):
        result = code_generator.generate_crud(sample_model)
        assert result is not None
        assert result.model_name == "User"
        assert result.generator_type == "crud"
        assert "UserCRUD" in result.content

    def test_generate_crud_no_primary_key(self, code_generator):
        model = ModelMeta(
            name="Test",
            fields=[FieldMeta(name="name", field_type=FieldType.STRING, python_type=str)],
        )
        with pytest.raises(ValidationError):
            code_generator.generate_crud(model)

    def test_generate_only_outputs_crud_for_models(self, code_generator, sample_model):
        code_generator.config.generate_data_layer = False
        result = code_generator.generate([sample_model])
        assert len(result) == 1
        assert result[0].generator_type == "crud"

    def test_generate_config(self, code_generator):
        result = code_generator.generate_config()
        assert result is not None
        assert result.file_path == "config.py"
        assert result.generator_type == "data_layer"

    def test_generate_database(self, code_generator):
        result = code_generator.generate_database()
        assert result is not None
        assert result.file_path == "database.py"
        assert result.generator_type == "data_layer"

    def test_generate_data_init(self, code_generator, sample_model):
        result = code_generator.generate_data_init([sample_model])
        assert result is not None
        assert result.file_path == "__init__.py"
        assert result.generator_type == "data_layer"

    def test_generate_data_layer(self, code_generator, sample_model):
        result = code_generator.generate_data_layer([sample_model])
        file_paths = [f.file_path for f in result]
        assert "config.py" in file_paths
        assert "database.py" in file_paths

    def test_generate_excludes_models(self, code_generator, sample_model):
        code_generator.config.exclude_models = ["User"]
        code_generator.config.generate_data_layer = False
        result = code_generator.generate([sample_model])
        assert result == []


class TestWriteFiles:
    """测试文件写入功能。"""

    def test_write_files_creates_directories(self, code_generator, tmp_path):
        code_generator.config.output_dir = str(tmp_path / "output")
        file = GeneratedFile(file_path="crud/test.py", content="# test content")
        code_generator.write_files([file])
        assert (tmp_path / "output/crud/test.py").exists()

    def test_write_files_content(self, code_generator, tmp_path):
        code_generator.config.output_dir = str(tmp_path / "output")
        file = GeneratedFile(file_path="test.py", content="# test content")
        code_generator.write_files([file])
        content = (tmp_path / "output/test.py").read_text(encoding="utf-8")
        assert content == "# test content"

    def test_write_files_dry_run(self, code_generator, tmp_path, capsys):
        code_generator.config.output_dir = str(tmp_path / "output")
        file = GeneratedFile(
            file_path="test.py",
            content="# test content",
            model_name="Test",
            generator_type="crud",
        )
        code_generator.write_files([file], dry_run=True)
        assert not (tmp_path / "output/test.py").exists()
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_generate_and_dry_run_should_not_copy_models(self, code_generator, tmp_path):
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "__init__.py").write_text("", encoding="utf-8")
        (models_dir / "user.py").write_text("class User: pass\n", encoding="utf-8")

        output_dir = tmp_path / "output"
        code_generator.config.models_path = str(models_dir)
        code_generator.config.output_dir = str(output_dir)
        code_generator.config.generate_data_layer = True
        code_generator.config.generate_model_copy = True

        file = GeneratedFile(
            file_path="config.py",
            content="# config",
            generator_type="data_layer",
        )
        code_generator.write_files([file], dry_run=True)
        assert not (output_dir / "models").exists()


class TestGenerateFunction:
    """测试 generate 便捷函数。"""

    def test_generate_path_conflict(self, tmp_path):
        output_dir = tmp_path / "app" / "generated"
        output_dir.mkdir(parents=True)
        models_dir = output_dir / "models"
        models_dir.mkdir()

        with pytest.raises(ValueError, match="不能位于"):
            generate(models_path=str(models_dir), output_dir=str(output_dir))

    def test_generate_path_conflict_uses_ascii_warning_on_gbk_stream(self, tmp_path):
        output_dir = tmp_path / "app" / "generated"
        output_dir.mkdir(parents=True)
        models_dir = output_dir / "models"
        models_dir.mkdir()

        stream = EncodedStringIO("gbk")
        with redirect_stdout(stream):
            with pytest.raises(ValueError):
                generate(models_path=str(models_dir), output_dir=str(output_dir))

        output = stream.getvalue()
        assert "[WARN]" in output
        assert "⚠" not in output

    def test_generate_rejects_unknown_argument(self, tmp_path):
        with pytest.raises(TypeError):
            generate(
                models_path=str(tmp_path / "models"),
                output_dir=str(tmp_path / "generated"),
                unexpected_option=True,
            )


class TestTemplateRendering:
    """测试模板渲染。"""

    def test_render_template(self, code_generator):
        context = {
            "config": code_generator.config,
            "db_name": "test.db",
            "db_dir": "AppData",
        }
        content = code_generator._render_template("config.py.j2", context)
        assert content is not None
        assert len(content) > 0

    def test_render_sync_database_template_uses_transaction_scope(
        self, code_generator
    ):
        content = code_generator._render_template("database.py.j2", {"config": code_generator.config})

        assert "@contextmanager" in content
        assert "def get_session(self)" in content
        assert "session.commit()" in content
        assert "session.rollback()" in content
        assert "db = DatabaseManager()" in content
        assert "def get_session()" in content
        assert "_instance" not in content
        assert "return Session(self.engine)" not in content

    def test_render_async_templates_generate_async_database_layer(
        self, generator_config
    ):
        generator_config.use_async = True
        generator = CodeGenerator(generator_config)

        config_content = generator._render_template(
            "config.py.j2",
            {"config": generator.config, "db_name": "test.db", "db_dir": None},
        )
        database_content = generator._render_template(
            "database.py.j2", {"config": generator.config}
        )
        init_content = generator._render_template(
            "data_init.py.j2",
            {"config": generator.config, "models": []},
        )

        assert "sqlite+aiosqlite:///" in config_content
        assert "@asynccontextmanager" in database_content
        assert "async def get_async_session(self)" in database_content
        assert "await session.commit()" in database_content
        assert "await session.rollback()" in database_content
        assert "async def init_database" in database_content
        assert '"get_async_session"' in init_content

    def test_render_invalid_template(self, code_generator):
        with pytest.raises(Exception):
            code_generator._render_template("nonexistent.j2", {})
