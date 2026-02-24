from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index


class Location(SQLModel, table=True):
    """📍 位置信息模型

    实现三级区域管理（1=楼栋→2=层数→3=房间），通过parent_id建立自引用层级关系。
    """

    __tablename__ = "location"

    # 定义部分索引：仅对未删除记录创建索引
    __table_args__ = (
        Index("idx_location_code", "code", unique=True, sqlite_where="is_deleted = 0"),
        Index("idx_location_hierarchy_level", "hierarchy_level", sqlite_where="is_deleted = 0"),
        Index("idx_location_parent_id", "parent_id", sqlite_where="is_deleted = 0"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(description="三级区域统一编码，例如：楼栋-层数-房间")
    name: str = Field(index=True, description="位置中文全称，便于人工识别")
    hierarchy_level: int = Field(description="区域层级：1=楼栋，2=层数，3=房间")
    parent_id: Optional[int] = Field(default=None, foreign_key="location.id", description="关联本表id，实现层级关联（一级位置无父级）")
    description: Optional[str] = Field(default=None, description="位置特性说明（如面积、用途）")
    tags: Optional[str] = Field(default=None, description="位置属性标签，多标签用逗号分隔")
    is_deleted: int = Field(default=0, description="软删除标记：0=未删除，1=已删除")
    created_at: datetime = Field(default_factory=datetime.now, description="数据创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="数据最后修改时间")

    # 关系定义
    parent: Optional["Location"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Location.id"}
    )
    children: List["Location"] = Relationship(back_populates="parent")
    construction_quantities: List["ConstructionQuantity"] = Relationship(back_populates="location")
