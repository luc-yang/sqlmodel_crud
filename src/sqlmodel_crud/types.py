"""CRUD 模块类型定义。"""

from typing import Any, Dict, TypeVar

from sqlmodel import SQLModel

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateInputType = TypeVar("CreateInputType", bound=SQLModel)
UpdateInputType = TypeVar("UpdateInputType", bound=SQLModel)
FilterDict = Dict[str, Any]

__all__ = [
    "ModelType",
    "CreateInputType",
    "UpdateInputType",
    "FilterDict",
]
