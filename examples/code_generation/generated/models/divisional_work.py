from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index


class DivisionalWork(SQLModel, table=True):
    """📐 分部工程模型

    存储单位工程下的分部工程信息（如土建、水电、装修），关联多个定额数据。
    """

    __tablename__ = "divisional_work"

    # 定义部分索引：仅对未删除记录创建唯一索引
    __table_args__ = (
        Index("idx_divisional_work_code", "code", unique=True, sqlite_where="is_deleted = 0"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(description="分部工程编码")
    name: str = Field(index=True, description="分部工程名称")
    description: Optional[str] = Field(default=None, description="分部工程范围、技术要求说明")
    tags: Optional[str] = Field(default=None, description="分部属性标签")
    is_deleted: int = Field(default=0, description="软删除标记：0=未删除，1=已删除")
    created_at: datetime = Field(default_factory=datetime.now, description="数据创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="数据最后修改时间")

    # 关系定义
    construction_quantities: List["ConstructionQuantity"] = Relationship(back_populates="divisional_work")
