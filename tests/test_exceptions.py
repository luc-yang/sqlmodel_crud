"""
异常类测试模块

测试所有 CRUD 异常类的行为和属性。
"""

import pytest
from sqlmodel_crud.exceptions import (
    ErrorCode,
    CRUDError,
    ValidationError,
    NotFoundError,
    DatabaseError,
    DuplicateError,
)


class TestErrorCode:
    """测试 ErrorCode 枚举"""

    def test_error_code_values(self):
        """测试错误码值正确"""
        assert ErrorCode.VALIDATION.value == "VALIDATION_ERROR"
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.DATABASE.value == "DATABASE_ERROR"
        assert ErrorCode.DUPLICATE.value == "DUPLICATE_ERROR"
        assert ErrorCode.UNKNOWN.value == "UNKNOWN_ERROR"

    def test_error_code_descriptions(self):
        """测试错误码描述正确"""
        assert ErrorCode.VALIDATION.description == "数据验证错误"
        assert ErrorCode.NOT_FOUND.description == "记录不存在"
        assert ErrorCode.DATABASE.description == "数据库操作错误"
        assert ErrorCode.DUPLICATE.description == "数据重复错误"
        assert ErrorCode.UNKNOWN.description == "未知错误"

    def test_from_string_valid(self):
        """测试从有效字符串获取枚举值"""
        assert ErrorCode.from_string("VALIDATION_ERROR") == ErrorCode.VALIDATION
        assert ErrorCode.from_string("NOT_FOUND") == ErrorCode.NOT_FOUND
        assert ErrorCode.from_string("DATABASE_ERROR") == ErrorCode.DATABASE

    def test_from_string_invalid(self):
        """测试从无效字符串获取枚举值返回 UNKNOWN"""
        assert ErrorCode.from_string("INVALID_CODE") == ErrorCode.UNKNOWN
        assert ErrorCode.from_string("") == ErrorCode.UNKNOWN


class TestCRUDError:
    """测试 CRUDError 基类"""

    def test_basic_initialization(self):
        """测试基本初始化"""
        error = CRUDError("测试错误消息")
        assert error.message == "测试错误消息"
        assert error.code == ErrorCode.UNKNOWN
        assert error.context == {}

    def test_initialization_with_code(self):
        """测试带错误码的初始化"""
        error = CRUDError("测试错误", code=ErrorCode.VALIDATION)
        assert error.code == ErrorCode.VALIDATION

    def test_initialization_with_context(self):
        """测试带上下文的初始化"""
        context = {"operation": "test", "user_id": 123}
        error = CRUDError("测试错误", context=context)
        assert error.context == context

    def test_str_method_basic(self):
        """测试 __str__ 方法基本格式"""
        error = CRUDError("测试错误消息")
        assert str(error) == "[UNKNOWN_ERROR] 测试错误消息"

    def test_str_method_with_context(self):
        """测试 __str__ 方法带上下文"""
        error = CRUDError("测试错误", context={"operation": "test", "id": 1})
        str_repr = str(error)
        assert "[UNKNOWN_ERROR] 测试错误" in str_repr
        assert "operation=test" in str_repr
        assert "id=1" in str_repr

    def test_to_dict(self):
        """测试 to_dict 方法"""
        error = CRUDError(
            "测试错误", code=ErrorCode.VALIDATION, context={"field": "name"}
        )
        result = error.to_dict()
        assert result["message"] == "测试错误"
        assert result["code"] == "VALIDATION_ERROR"
        assert result["description"] == "数据验证错误"
        assert result["context"] == {"field": "name"}

    def test_inheritance_from_exception(self):
        """测试继承自 Exception"""
        error = CRUDError("测试")
        assert isinstance(error, Exception)


class TestValidationError:
    """测试 ValidationError 验证错误类"""

    def test_default_code(self):
        """测试默认错误码为 VALIDATION"""
        error = ValidationError("验证失败")
        assert error.code == ErrorCode.VALIDATION

    def test_field_and_errors(self):
        """测试 field 和 errors 属性"""
        errors = {"min": 5, "max": 100}
        error = ValidationError("字段验证失败", field="username", errors=errors)
        assert error.field == "username"
        assert error.errors == errors
        assert error.context["field"] == "username"
        assert error.context["errors"] == errors

    def test_errors_default_empty_dict(self):
        """测试 errors 默认为空字典"""
        error = ValidationError("验证失败")
        assert error.errors == {}

    def test_str_method_with_field(self):
        """测试 __str__ 方法包含字段信息"""
        error = ValidationError("字段验证失败", field="username")
        assert "field=username" in str(error)

    def test_inheritance(self):
        """测试 ValidationError 继承自 CRUDError"""
        error = ValidationError("验证失败")
        assert isinstance(error, CRUDError)

    def test_additional_context(self):
        """测试额外的上下文参数"""
        error = ValidationError("验证失败", field="name", custom_key="custom_value")
        assert error.context["custom_key"] == "custom_value"


class TestNotFoundError:
    """测试 NotFoundError 记录不存在错误类"""

    def test_default_code(self):
        """测试默认错误码为 NOT_FOUND"""
        error = NotFoundError()
        assert error.code == ErrorCode.NOT_FOUND

    def test_auto_message_with_resource_and_identifier(self):
        """测试自动消息生成（传入 resource 和 identifier）"""
        error = NotFoundError(resource="User", identifier=123)
        assert error.message == "未找到 User 记录 (标识符: 123)"
        assert error.resource == "User"
        assert error.identifier == 123

    def test_auto_message_with_string_identifier(self):
        """测试自动消息生成（使用字符串标识符）"""
        error = NotFoundError(resource="Post", identifier="abc-123")
        assert error.message == "未找到 Post 记录 (标识符: abc-123)"

    def test_default_message_without_resource(self):
        """测试无资源信息时的默认消息"""
        error = NotFoundError()
        assert error.message == "请求的记录不存在"
        assert error.resource is None
        assert error.identifier is None

    def test_custom_message_override(self):
        """测试自定义消息覆盖自动生成的消息"""
        error = NotFoundError(message="自定义错误消息", resource="User", identifier=123)
        assert error.message == "自定义错误消息"
        assert error.resource == "User"
        assert error.identifier == 123

    def test_context_contains_resource_and_identifier(self):
        """测试上下文包含 resource 和 identifier"""
        error = NotFoundError(resource="User", identifier=123)
        assert error.context["resource"] == "User"
        assert error.context["identifier"] == 123

    def test_inheritance(self):
        """测试 NotFoundError 继承自 CRUDError"""
        error = NotFoundError()
        assert isinstance(error, CRUDError)


class TestDatabaseError:
    """测试 DatabaseError 数据库操作错误类"""

    def test_default_code(self):
        """测试默认错误码为 DATABASE"""
        error = DatabaseError("数据库错误")
        assert error.code == ErrorCode.DATABASE

    def test_operation_and_original(self):
        """测试 operation 和 original 属性"""
        original = Exception("连接超时")
        error = DatabaseError("数据库连接失败", operation="connect", original=original)
        assert error.operation == "connect"
        assert error.original == original
        assert error.context["operation"] == "connect"
        assert error.context["original_error"] == "连接超时"

    def test_str_method_with_operation(self):
        """测试 __str__ 方法包含操作信息"""
        error = DatabaseError("数据库查询失败", operation="query")
        assert "operation=query" in str(error)

    def test_str_method_with_original(self):
        """测试 __str__ 方法包含原始错误"""
        original = Exception("语法错误")
        error = DatabaseError("SQL执行失败", original=original)
        assert "original_error=语法错误" in str(error)

    def test_inheritance(self):
        """测试 DatabaseError 继承自 CRUDError"""
        error = DatabaseError("数据库错误")
        assert isinstance(error, CRUDError)


class TestDuplicateError:
    """测试 DuplicateError 重复数据错误类"""

    def test_default_code(self):
        """测试默认错误码为 DUPLICATE"""
        error = DuplicateError()
        assert error.code == ErrorCode.DUPLICATE

    def test_auto_message_with_field_and_value(self):
        """测试自动消息生成（传入 field 和 value）"""
        error = DuplicateError(field="email", value="test@example.com")
        assert error.message == "字段 'email' 的值 'test@example.com' 已存在"
        assert error.field == "email"
        assert error.value == "test@example.com"

    def test_auto_message_with_integer_value(self):
        """测试自动消息生成（使用整数值）"""
        error = DuplicateError(field="id", value=42)
        assert error.message == "字段 'id' 的值 '42' 已存在"

    def test_default_message_without_field(self):
        """测试无字段信息时的默认消息"""
        error = DuplicateError()
        assert error.message == "记录已存在，违反唯一约束"
        assert error.field is None
        assert error.value is None

    def test_custom_message_override(self):
        """测试自定义消息覆盖自动生成的消息"""
        error = DuplicateError(
            message="自定义重复错误", field="email", value="test@example.com"
        )
        assert error.message == "自定义重复错误"
        assert error.field == "email"
        assert error.value == "test@example.com"

    def test_context_contains_field_and_value(self):
        """测试上下文包含 field 和 value"""
        error = DuplicateError(field="username", value="admin")
        assert error.context["field"] == "username"
        assert error.context["value"] == "admin"

    def test_inheritance(self):
        """测试 DuplicateError 继承自 CRUDError"""
        error = DuplicateError()
        assert isinstance(error, CRUDError)


class TestExceptionChaining:
    """测试异常链"""

    def test_validation_error_chaining(self):
        """测试 ValidationError 异常链"""
        original = ValueError("原始错误")
        try:
            raise ValidationError("验证失败") from original
        except ValidationError as e:
            assert e.__cause__ == original

    def test_database_error_chaining(self):
        """测试 DatabaseError 异常链"""
        original = RuntimeError("数据库连接失败")
        try:
            raise DatabaseError("操作失败", original=original) from original
        except DatabaseError as e:
            assert e.__cause__ == original
            assert e.original == original
