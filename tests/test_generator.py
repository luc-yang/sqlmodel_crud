"""
代码生成器模块测试

测试 sqlmodel_crud.generator 模块的所有功能，包括：
- CodeGenerator 类：代码生成核心类
- GeneratedFile 类：生成文件的数据类
- generate 便捷函数：一键生成代码
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Optional, List

from sqlmodel_crud.generator import (
    GeneratedFile,
    CodeGenerator,
    generate,
    CRUDGenerator,
)
from sqlmodel_crud.config import GeneratorConfig
from sqlmodel_crud.scanner import ModelMeta, FieldMeta, FieldType
from sqlmodel_crud.exceptions import ValidationError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def generator_config(tmp_path):
    """创建生成器配置 fixture"""
    return GeneratorConfig(
        models_path=str(tmp_path / "models"),
        output_dir=str(tmp_path / "generated"),
        generators=["crud"],
        crud_suffix="CRUD",
    )


@pytest.fixture
def code_generator(generator_config):
    """创建代码生成器 fixture"""
    return CodeGenerator(generator_config)


@pytest.fixture
def sample_model():
    """创建示例模型元数据 fixture"""
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


# =============================================================================
# Test GeneratedFile
# =============================================================================


class TestGeneratedFile:
    """测试 GeneratedFile 数据类"""

    def test_generated_file_creation(self):
        """测试创建 GeneratedFile 实例"""
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
        """测试 GeneratedFile 可选字段"""
        file = GeneratedFile(
            file_path="test.py",
            content="content",
        )
        assert file.model_name is None
        assert file.generator_type == ""


# =============================================================================
# Test CodeGenerator Initialization
# =============================================================================


class TestCodeGeneratorInit:
    """测试 CodeGenerator 初始化"""

    def test_init_with_config(self, generator_config):
        """测试使用配置初始化"""
        generator = CodeGenerator(generator_config)
        assert generator.config == generator_config
        assert generator.generated_files == []
        assert generator.jinja_env is not None

    def test_init_sets_up_jinja_env(self, generator_config):
        """测试初始化设置 Jinja2 环境"""
        generator = CodeGenerator(generator_config)
        assert generator.jinja_env is not None
        # 验证过滤器是否已注册
        assert "snake_case" in generator.jinja_env.filters
        assert "pascal_case" in generator.jinja_env.filters
        assert "camel_case" in generator.jinja_env.filters


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestHelperMethods:
    """测试辅助方法"""

    def test_to_snake_case(self, code_generator):
        """测试转换为蛇形命名"""
        assert code_generator._to_snake_case("User") == "user"
        assert code_generator._to_snake_case("UserProfile") == "user_profile"
        assert code_generator._to_snake_case("APIKey") == "api_key"
        assert code_generator._to_snake_case("test_name") == "test_name"

    def test_to_pascal_case(self, code_generator):
        """测试转换为帕斯卡命名"""
        assert code_generator._to_pascal_case("user") == "User"
        assert code_generator._to_pascal_case("user_profile") == "UserProfile"
        assert code_generator._to_pascal_case("api_key") == "ApiKey"

    def test_to_camel_case(self, code_generator):
        """测试转换为驼峰命名"""
        assert code_generator._to_camel_case("user") == "user"
        assert code_generator._to_camel_case("user_profile") == "userProfile"
        assert code_generator._to_camel_case("api_key") == "apiKey"

    def test_get_primary_key_field(self, code_generator, sample_model):
        """测试获取主键字段"""
        pk_field = code_generator._get_primary_key_field(sample_model)
        assert pk_field is not None
        assert pk_field.name == "id"
        assert pk_field.primary_key is True

    def test_get_primary_key_field_no_pk(self, code_generator):
        """测试获取主键字段 - 无主键但有名称为 id 的字段"""
        id_field = FieldMeta(name="id", field_type=FieldType.INTEGER, python_type=int)
        model = ModelMeta(name="Test", fields=[id_field])
        pk_field = code_generator._get_primary_key_field(model)
        assert pk_field is not None
        assert pk_field.name == "id"

    def test_get_primary_key_field_none(self, code_generator):
        """测试获取主键字段 - 完全没有 id 字段"""
        name_field = FieldMeta(
            name="name", field_type=FieldType.STRING, python_type=str
        )
        model = ModelMeta(name="Test", fields=[name_field])
        pk_field = code_generator._get_primary_key_field(model)
        assert pk_field is None

    def test_format_type_basic(self, code_generator):
        """测试格式化基本类型"""
        assert code_generator._format_type(str) == "str"
        assert code_generator._format_type(int) == "int"
        assert code_generator._format_type(float) == "float"
        assert code_generator._format_type(bool) == "bool"

    def test_format_type_optional(self, code_generator):
        """测试格式化 Optional 类型"""
        from typing import Optional

        result = code_generator._format_type(Optional[int])
        assert "Optional" in result
        assert "int" in result

    def test_format_type_list(self, code_generator):
        """测试格式化 List 类型"""
        from typing import List

        result = code_generator._format_type(List[str])
        assert result == "List[str]"

    def test_format_type_none(self, code_generator):
        """测试格式化 None 类型"""
        assert code_generator._format_type(None) == "Any"

    def test_get_type_import_datetime(self, code_generator):
        """测试获取 datetime 导入语句"""
        result = code_generator._get_type_import(datetime)
        assert "datetime import datetime" in result

    def test_get_type_import_basic_types(self, code_generator):
        """测试获取基本类型的导入语句"""
        assert code_generator._get_type_import(str) == ""
        assert code_generator._get_type_import(int) == ""

    def test_get_output_path_crud(self, code_generator):
        """测试获取 CRUD 输出路径"""
        path = code_generator._get_output_path("crud", "User")
        assert path == Path("crud/user.py")

    def test_get_output_path_schemas(self, code_generator):
        """测试获取 schemas 输出路径"""
        path = code_generator._get_output_path("schemas", "UserProfile")
        assert path == Path("schemas/user_profile.py")

    def test_generate_file_header(self, code_generator):
        """测试生成文件头"""
        header = code_generator._generate_file_header("User", "CRUD")
        assert "User" in header
        assert "CRUD" in header
        assert "自动生成" in header


# =============================================================================
# Test Generate Methods
# =============================================================================


class TestGenerateMethods:
    """测试生成方法"""

    def test_generate_crud(self, code_generator, sample_model):
        """测试生成 CRUD 代码"""
        result = code_generator.generate_crud(sample_model)
        assert result is not None
        assert result.model_name == "User"
        assert result.generator_type == "crud"
        assert "UserCRUD" in result.content

    def test_generate_crud_no_primary_key(self, code_generator):
        """测试生成 CRUD - 无主键"""
        name_field = FieldMeta(
            name="name", field_type=FieldType.STRING, python_type=str
        )
        model = ModelMeta(name="Test", fields=[name_field])

        with pytest.raises(ValidationError):
            code_generator.generate_crud(model)

    def test_generate_schemas(self, code_generator, sample_model):
        """测试生成 Schema 代码"""
        # 修改配置以包含 schemas 生成器
        code_generator.config.generators = ["schemas"]
        result = code_generator.generate_schemas(sample_model)
        assert len(result) > 0
        assert result[0].model_name == "User"
        assert result[0].generator_type == "schemas"

    def test_generate_config(self, code_generator):
        """测试生成 config.py"""
        result = code_generator.generate_config()
        assert result is not None
        assert result.file_path == "config.py"
        assert result.generator_type == "data_layer"

    def test_generate_database(self, code_generator):
        """测试生成 database.py"""
        result = code_generator.generate_database()
        assert result is not None
        assert result.file_path == "database.py"
        assert result.generator_type == "data_layer"

    def test_generate_data_init(self, code_generator, sample_model):
        """测试生成数据层 __init__.py"""
        result = code_generator.generate_data_init([sample_model])
        assert result is not None
        assert result.file_path == "__init__.py"
        assert result.generator_type == "data_layer"

    def test_generate_data_layer(self, code_generator, sample_model):
        """测试生成数据层基础设施文件"""
        result = code_generator.generate_data_layer([sample_model])
        assert len(result) >= 2
        file_paths = [f.file_path for f in result]
        assert "config.py" in file_paths
        assert "database.py" in file_paths

    def test_generate_all(self, code_generator, sample_model):
        """测试生成所有代码"""
        code_generator.config.generators = ["crud"]
        code_generator.config.generate_data_layer = True

        result = code_generator.generate([sample_model])
        assert len(result) > 0

    def test_generate_excludes_models(self, code_generator, sample_model):
        """测试排除模型"""
        code_generator.config.exclude_models = ["User"]
        code_generator.config.generators = ["crud"]
        code_generator.config.generate_data_layer = False

        result = code_generator.generate([sample_model])
        # User 模型被排除，应该没有生成的文件
        model_files = [f for f in result if f.model_name == "User"]
        assert len(model_files) == 0


# =============================================================================
# Test Write Files
# =============================================================================


class TestWriteFiles:
    """测试文件写入功能"""

    def test_write_files_creates_directories(self, code_generator, tmp_path):
        """测试写入文件创建目录"""
        code_generator.config.output_dir = str(tmp_path / "output")

        file = GeneratedFile(
            file_path="crud/test.py",
            content="# test content",
        )

        code_generator.write_files([file])

        assert (tmp_path / "output/crud/test.py").exists()

    def test_write_files_content(self, code_generator, tmp_path):
        """测试写入文件内容正确"""
        code_generator.config.output_dir = str(tmp_path / "output")

        file = GeneratedFile(
            file_path="test.py",
            content="# test content",
        )

        code_generator.write_files([file])

        content = (tmp_path / "output/test.py").read_text(encoding="utf-8")
        assert content == "# test content"

    def test_write_files_dry_run(self, code_generator, tmp_path, capsys):
        """测试预览模式不写入文件"""
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


# =============================================================================
# Test CRUDGenerator Alias
# =============================================================================


class TestCRUDGeneratorAlias:
    """测试 CRUDGenerator 别名"""

    def test_crud_generator_is_alias(self):
        """测试 CRUDGenerator 是 CodeGenerator 的别名"""
        assert CRUDGenerator is CodeGenerator


# =============================================================================
# Test Generate Function
# =============================================================================


class TestGenerateFunction:
    """测试 generate 便捷函数"""

    def test_generate_path_conflict(self, tmp_path):
        """测试路径冲突检测"""
        # 创建一个嵌套结构，使 models_path 位于 output_dir 内
        output_dir = tmp_path / "app" / "generated"
        output_dir.mkdir(parents=True)
        models_dir = output_dir / "models"
        models_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            generate(
                models_path=str(models_dir),
                output_dir=str(output_dir),
            )

        assert "不能位于" in str(exc_info.value)


# =============================================================================
# Test Template Rendering
# =============================================================================


class TestTemplateRendering:
    """测试模板渲染"""

    def test_render_template(self, code_generator):
        """测试渲染模板"""
        # 使用内置的 config.py.j2 模板
        context = {
            "config": code_generator.config,
            "db_name": "test.db",
            "db_dir": "AppData",
        }

        content = code_generator._render_template("config.py.j2", context)
        assert content is not None
        assert len(content) > 0

    def test_render_invalid_template(self, code_generator):
        """测试渲染不存在的模板"""
        with pytest.raises(Exception):
            code_generator._render_template("nonexistent.j2", {})
