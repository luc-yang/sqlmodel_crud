from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index


class Quota(SQLModel, table=True):
    """📋 定额数据模型

    存储定额模板数据，包含册名、章节名、定额编码、工日、工作内容等信息。
    """

    __tablename__ = "quota"

    # 定义部分索引：仅对未删除记录创建索引
    __table_args__ = (
        Index("idx_quota_code", "code", unique=True, sqlite_where="is_deleted = 0"),
        Index("idx_quota_volume_chapter", "volume_name", "chapter_name", sqlite_where="is_deleted = 0"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    volume_name: str = Field(description="定额所在册的名称")
    chapter_name: str = Field(description="定额所在章的名称")
    code: str = Field(description="定额标准编码")
    name: str = Field(index=True, description="定额对应的施工任务名称")
    measurement_unit: str = Field(description="定额计算单位")
    workday: Optional[float] = Field(default=None, description="完成该任务所需工日")
    work_content: str = Field(description="详细施工步骤与范围")
    resources: Optional[str] = Field(default=None, description="所需材料/人工/机械，JSON格式存储")
    description: Optional[str] = Field(default=None, description="定额调整说明、特殊要求")
    tags: Optional[str] = Field(default=None, description="定额属性标签")
    is_deleted: int = Field(default=0, description="软删除标记：0=未删除，1=已删除")
    created_at: datetime = Field(default_factory=datetime.now, description="数据创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="数据最后修改时间")

    # 关系定义
    construction_quantities: List["ConstructionQuantity"] = Relationship(back_populates="quota")
