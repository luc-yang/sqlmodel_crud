"""
该文件由 SQLModel CRUD 生成器自动生成。

模型: Location
类型: CRUD
生成时间: 2026-02-27 13:26:43

警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""


from typing import Optional, Any, Dict, List, Union
from sqlmodel import Session
from sqlmodel_crud import CRUDBase

from ..models.location import Location

class LocationCRUD(CRUDBase[Location, Location, Location]):
    """
    Location 模型的 CRUD 操作类。

    继承自 CRUDBase，
    自动拥有完整的数据库操作能力，包括：
    - create, create_multi (批量创建)
    - get, get_or_raise, get_multi (查询，支持分页、过滤、排序)
    - update, delete (更新、删除，支持软删除)
    - count, exists (统计、存在性检查)
    - 软删除自动过滤
    - 统一异常处理

    索引字段:
    - name: str
    注意: 本表包含部分索引（Partial Index），使用索引字段查询时请注意 WHERE 条件。

    用法示例:
        >>> crud = LocationCRUD()
        >>> obj = crud.create(session, {"name": "test"})
    """

    def __init__(self):
        """
        初始化 CRUD 操作类。

        按照 MVP 架构设计，传入模型类型而非数据库会话。
        会话应通过方法参数传入，支持会话复用和事务管理。
        """
        super().__init__(Location)


    # ==================== 基于普通索引的查询方法 ====================

def get_by_name(
        self,
        session: Session,
        name: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Location]:
        """
        根据 name 获取多条记录（利用索引）。

        Args:
            session: 数据库会话
            name: 位置中文全称，便于人工识别
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            记录对象列表

        示例:
            >>> objs = crud.get_by_name(session, "value")
        """
        from sqlmodel import select

        statement = (
            select(self.model)
            .where(self.model.name == name)
            .offset(skip)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

def count_by_name(
        self,
        session: Session,
        name: str
    ) -> int:
        """
        根据 name 统计记录数（利用索引）。

        Args:
            session: 数据库会话
            name: 位置中文全称，便于人工识别

        Returns:
            符合条件的记录总数

        示例:
            >>> count = crud.count_by_name(session, "value")
        """
        from sqlmodel import select, func

        statement = select(func.count()).select_from(self.model).where(
            self.model.name == name
        )
        return session.execute(statement).scalar() or 0

