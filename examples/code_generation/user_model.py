"""
示例模型定义文件

这个文件定义了 User 模型，用于代码生成器的示例。
在实际项目中，你应该将模型文件放在单独的目录中，
例如：app/models/ 或 TestData/models/
"""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


# 定义实体模型
class User(SQLModel, table=True):
    """👤 用户模型"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    age: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
