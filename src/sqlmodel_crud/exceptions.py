"""异常定义。"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """错误码枚举。"""

    VALIDATION = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DATABASE = "DATABASE_ERROR"
    DUPLICATE = "DUPLICATE_ERROR"
    UNKNOWN = "UNKNOWN_ERROR"

    @property
    def description(self) -> str:
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
        try:
            return cls(code_str)
        except ValueError:
            return cls.UNKNOWN


class CRUDError(Exception):
    """基础异常。"""

    default_code: ErrorCode = ErrorCode.UNKNOWN

    def __init__(
        self,
        message: str,
        *,
        code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.context = context or {}

    def __str__(self) -> str:
        parts = [f"[{self.code.value}] {self.message}"]
        context_str = self._format_context()
        if context_str:
            parts.append(context_str)
        return " | ".join(parts)

    def _format_context(self) -> str:
        if not self.context:
            return ""

        context_parts = []
        for key, value in self.context.items():
            if value is not None:
                context_parts.append(f"{key}={value}")

        return "; ".join(context_parts) if context_parts else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "code": self.code.value,
            "description": self.code.description,
            "context": self.context,
        }


class ValidationError(CRUDError):
    """数据验证异常。"""

    default_code = ErrorCode.VALIDATION

    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
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
    """未找到资源异常。"""

    default_code = ErrorCode.NOT_FOUND

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        resource: Optional[str] = None,
        identifier: Any = None,
        **kwargs,
    ):
        if message is None:
            if resource:
                message = f"未找到 {resource} 记录"
                if identifier is not None:
                    message += f" (标识符: {identifier})"
            else:
                message = "请求的记录不存在"

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
    """数据库操作异常。"""

    default_code = ErrorCode.DATABASE

    def __init__(
        self,
        message: str,
        *,
        operation: Optional[str] = None,
        original: Optional[Exception] = None,
        **kwargs,
    ):
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
    """唯一约束冲突异常。"""

    default_code = ErrorCode.DUPLICATE

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs,
    ):
        if message is None:
            if field and value is not None:
                message = f"字段 '{field}' 的值 '{value}' 已存在"
            else:
                message = "记录已存在，违反唯一约束"

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
