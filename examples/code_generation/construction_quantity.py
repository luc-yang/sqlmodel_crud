from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ConstructionQuantity(SQLModel, table=True):
    """🔨 施工工程量模型

    存储分页工程量具体数量，关联分部工程与具体位置，是分页工程量统计的核心表。
    """

    __tablename__ = "construction_quantity"

    id: Optional[int] = Field(default=None, primary_key=True)
    unit_project_id: int = Field(foreign_key="unit_project.id", index=True, description="外键，关联单位工程表")
    divisional_work_id: int = Field(foreign_key="divisional_work.id", index=True, description="外键，关联分部工程表")
    location_id: int = Field(foreign_key="location.id", index=True, description="外键，关联位置信息表")
    quota_id: int = Field(foreign_key="quota.id", index=True, description="外键，关联定额数据表")
    quantity: float = Field(description="该施工任务的工程量（如10套、20㎡）")
    resources: Optional[str] = Field(default=None, description="基于定额调整后的资源，JSON格式")
    description: Optional[str] = Field(default=None, description="该施工任务的特殊说明（如调整原因）")
    tags: Optional[str] = Field(default=None, description="多标签逗号分隔")
    is_deleted: int = Field(default=0, description="软删除标记：0=未删除，1=已删除")
    created_at: datetime = Field(default_factory=datetime.now, description="数据创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="数据最后修改时间")

    # 关系定义
    unit_project: Optional["UnitProject"] = Relationship(back_populates="construction_quantities")
    divisional_work: Optional["DivisionalWork"] = Relationship(back_populates="construction_quantities")
    location: Optional["Location"] = Relationship(back_populates="construction_quantities")
    quota: Optional["Quota"] = Relationship(back_populates="construction_quantities")
