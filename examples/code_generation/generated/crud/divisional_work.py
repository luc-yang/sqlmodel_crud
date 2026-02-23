"""
该文件由 SQLModel CRUD 生成器自动生成。

模型: DivisionalWork
类型: CRUD
生成时间: 2026-02-23 21:15:42

警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""


from typing import Optional, Any, Dict, List
from sqlmodel import Session
from sqlmodel_crud import CRUDBase

from ..models.divisional_work import DivisionalWork

class DivisionalWorkCRUD(CRUDBase[DivisionalWork, DivisionalWork, DivisionalWork]):
    """
    DivisionalWork 模型的 CRUD 操作类。

    继承自 CRUDBase，
    自动拥有完整的数据库操作能力，包括：
    - create, create_multi (批量创建)
    - get, get_or_raise, get_multi (查询，支持分页、过滤、排序)
    - update, delete (更新、删除，支持软删除)
    - count, exists (统计、存在性检查)
    - 软删除自动过滤
    - 统一异常处理

    用法示例:
        >>> crud = DivisionalWorkCRUD()
        >>> obj = crud.create(session, {"name": "test"})
    """

    def __init__(self):
        """
        初始化 CRUD 操作类。

        按照 MVP 架构设计，传入模型类型而非数据库会话。
        会话应通过方法参数传入，支持会话复用和事务管理。
        """
        super().__init__(DivisionalWork)

