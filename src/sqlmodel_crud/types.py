"""
CRUD 模块类型定义模块

提供泛型类型变量和辅助类型定义，支持完整的类型提示。
"""

from typing import TypeVar, Dict, Any
from sqlmodel import SQLModel

# 模型类型变量 - 用于 SQLModel 实体类
ModelType = TypeVar("ModelType", bound=SQLModel)
"""SQLModel 实体模型类型变量

用于绑定具体的 SQLModel 子类，提供类型安全。
"""

# 创建模式类型变量 - 用于创建操作的数据验证模型
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
"""创建操作的数据验证模型类型变量

用于绑定创建操作使用的 Pydantic/SQLModel 验证模型。
通常包含创建记录时需要的所有字段。
"""

# 更新模式类型变量 - 用于更新操作的数据验证模型
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)
"""更新操作的数据验证模型类型变量

用于绑定更新操作使用的 Pydantic/SQLModel 验证模型。
通常所有字段都是可选的，允许部分更新。
"""

# 过滤器类型别名 - 用于查询过滤条件
FilterDict = Dict[str, Any]
"""过滤器字典类型

用于传递查询过滤条件，键为字段名，值为过滤值。
示例: {"name": "张三", "age": 25}
"""


__all__ = [
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType",
    "FilterDict",
]
