"""
CRUD 模块异常处理模块

提供统一的异常处理机制，包含数据验证和友好的错误提示。
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """CRUD 错误码枚举

    提供标准化的错误码分类，便于错误识别和处理。

    Attributes:
        value: 错误码字符串值
        description: 错误码中文描述

    示例:
        >>> try:
        ...     # 某些 CRUD 操作
        ... except CRUDError as e:
        ...     if e.code == ErrorCode.NOT_FOUND:
        ...         print("记录不存在")
    """

    VALIDATION = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DATABASE = "DATABASE_ERROR"
    DUPLICATE = "DUPLICATE_ERROR"
    UNKNOWN = "UNKNOWN_ERROR"

    @property
    def description(self) -> str:
        """获取错误码的中文描述"""
        descriptions = {
            ErrorCode.VALIDATION: "数据验证错误",
            ErrorCode.NOT_FOUND: "记录不存在",
            ErrorCode.DATABASE: "数据库操作错误",
            ErrorCode.DUPLICATE: "数据重复错误",
            ErrorCode.UNKNOWN: "未知错误",
        }
        return descriptions.get(self, "未知错误")

    @classmethod
    def from_string(cls, code_str: str) -> "ErrorCode":
        """从字符串获取错误码枚举值

        Args:
            code_str: 错误码字符串

        Returns:
            对应的 ErrorCode 枚举值，如果不存在则返回 UNKNOWN

        示例:
            >>> code = ErrorCode.from_string("VALIDATION_ERROR")
            >>> print(code)
            ErrorCode.VALIDATION
        """
        try:
            return cls(code_str)
        except ValueError:
            return cls.UNKNOWN


class CRUDError(Exception):
    """CRUD 基础异常类

    所有 CRUD 相关异常的基类，提供统一的错误处理接口。

    Attributes:
        message: 错误描述信息
        code: 错误码枚举值
        context: 错误上下文信息字典

    示例:
        >>> try:
        ...     # 某些 CRUD 操作
        ... except CRUDError as e:
        ...     print(f"错误 [{e.code.value}]: {e.message}")
    """

    # 默认错误码，子类可覆盖
    default_code: ErrorCode = ErrorCode.UNKNOWN

    def __init__(
        self,
        message: str,
        *,
        code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """初始化 CRUD 异常

        Args:
            message: 错误描述信息
            code: 错误码枚举值，默认为 UNKNOWN
            context: 错误上下文信息字典
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.context = context or {}

    def __str__(self) -> str:
        """返回错误字符串表示"""
        parts = [f"[{self.code.value}] {self.message}"]

        # 添加上下文信息
        context_str = self._format_context()
        if context_str:
            parts.append(context_str)

        return " | ".join(parts)

    def _format_context(self) -> str:
        """格式化上下文信息为字符串

        Returns:
            格式化后的上下文字符串，如果没有上下文则返回空字符串
        """
        if not self.context:
            return ""

        context_parts = []
        for key, value in self.context.items():
            if value is not None:
                context_parts.append(f"{key}={value}")

        return "; ".join(context_parts) if context_parts else ""

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典表示

        Returns:
            包含异常信息的字典

        示例:
            >>> error = CRUDError("测试错误", code=ErrorCode.VALIDATION)
            >>> error.to_dict()
            {'message': '测试错误', 'code': 'VALIDATION_ERROR', 'context': {}}
        """
        return {
            "message": self.message,
            "code": self.code.value,
            "description": self.code.description,
            "context": self.context,
        }


class ValidationError(CRUDError):
    """数据验证异常

    当输入数据不符合要求时抛出，例如参数缺失、格式错误等。

    Attributes:
        message: 验证失败的详细说明
        field: 验证失败的字段名
        errors: 详细的验证错误信息字典

    示例:
        >>> raise ValidationError("邮箱格式不正确", field="email")
        >>> raise ValidationError("年龄必须在 18-100 之间", field="age")
    """

    default_code = ErrorCode.VALIDATION

    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """初始化验证异常

        Args:
            message: 验证失败的详细说明
            field: 验证失败的字段名
            errors: 详细的验证错误信息字典
            **kwargs: 额外的上下文参数
        """
        # 构建上下文
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        if errors:
            context["errors"] = errors
        context.update(kwargs)

        super().__init__(message, context=context)
        self.field = field
        self.errors = errors or {}


class NotFoundError(CRUDError):
    """记录不存在异常

    当查询的记录不存在时抛出，通常用于 get_by_id 等操作。

    Attributes:
        message: 错误描述信息
        resource: 查询的资源类型名称
        identifier: 查询的标识符

    示例:
        >>> raise NotFoundError(resource="User", identifier=123)
        >>> raise NotFoundError("自定义错误消息", resource="Product", identifier="SKU001")
    """

    default_code = ErrorCode.NOT_FOUND

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        resource: Optional[str] = None,
        identifier: Any = None,
        **kwargs,
    ):
        """初始化不存在异常

        Args:
            message: 自定义错误消息，如果不提供则自动生成
            resource: 查询的资源类型名称
            identifier: 查询的标识符
            **kwargs: 额外的上下文参数
        """
        # 自动生成消息
        if message is None:
            if resource:
                message = f"未找到 {resource} 记录"
                if identifier is not None:
                    message += f" (标识符: {identifier})"
            else:
                message = "请求的记录不存在"

        # 构建上下文
        context = kwargs.pop("context", {})
        if resource:
            context["resource"] = resource
        if identifier is not None:
            context["identifier"] = identifier
        context.update(kwargs)

        super().__init__(message, context=context)
        self.resource = resource
        self.identifier = identifier


class DatabaseError(CRUDError):
    """数据库操作异常

    当数据库操作失败时抛出，包含连接错误、执行错误等。

    Attributes:
        message: 错误描述信息
        operation: 发生错误的操作类型
        original: 原始异常对象

    示例:
        >>> try:
        ...     session.execute(query)
        ... except SQLAlchemyError as e:
        ...     raise DatabaseError("查询失败", original=e, operation="query")
    """

    default_code = ErrorCode.DATABASE

    def __init__(
        self,
        message: str,
        *,
        operation: Optional[str] = None,
        original: Optional[Exception] = None,
        **kwargs,
    ):
        """初始化数据库异常

        Args:
            message: 错误描述信息
            operation: 发生错误的操作类型（如 query, insert, update）
            original: 原始异常对象
            **kwargs: 额外的上下文参数
        """
        # 构建上下文
        context = kwargs.pop("context", {})
        if operation:
            context["operation"] = operation
        if original:
            context["original_error"] = str(original)
        context.update(kwargs)

        super().__init__(message, context=context)
        self.operation = operation
        self.original = original


class DuplicateError(CRUDError):
    """重复记录异常

    当尝试创建或更新记录时违反唯一约束时抛出。

    Attributes:
        message: 错误描述信息
        field: 重复的字段名
        value: 重复的值

    示例:
        >>> raise DuplicateError(field="email", value="user@example.com")
        >>> raise DuplicateError("该用户名已被注册")
    """

    default_code = ErrorCode.DUPLICATE

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs,
    ):
        """初始化重复异常

        Args:
            message: 自定义错误消息，如果不提供则自动生成
            field: 重复的字段名
            value: 重复的值
            **kwargs: 额外的上下文参数
        """
        # 自动生成消息
        if message is None:
            if field and value is not None:
                message = f"字段 '{field}' 的值 '{value}' 已存在"
            else:
                message = "记录已存在，违反唯一约束"

        # 构建上下文
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = value
        context.update(kwargs)

        super().__init__(message, context=context)
        self.field = field
        self.value = value


__all__ = [
    "ErrorCode",
    "CRUDError",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    "DuplicateError",
]
