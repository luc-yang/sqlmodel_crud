from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class UnitProject(SQLModel, table=True):
    """🏗️ 单位工程模型

    存储项目整体信息，作为最高层级的数据容器，关联多个分部工程。
    """

    __tablename__ = "unit_project"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, description="单位工程唯一编码")
    name: str = Field(index=True, description="单位工程完整名称")
    description: Optional[str] = Field(default=None, description="项目概况、建设范围等说明")
    tags: Optional[str] = Field(default=None, description="用于分类筛选，多标签用逗号分隔")
    is_deleted: int = Field(default=0, description="软删除标记：0=未删除，1=已删除")
    created_at: datetime = Field(default_factory=datetime.now, description="记录数据创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="记录数据最后修改时间")

    # 关系定义
    construction_quantities: List["ConstructionQuantity"] = Relationship(back_populates="unit_project")
