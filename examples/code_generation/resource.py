from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Resource(SQLModel, table=True):
    """📦 物资模型

    存储物资的模板数据，便于用户快速填入资源数据。
    物资表仅作为参考模板使用，定额表、工程量表中的物资信息均以JSON格式存储。
    """

    __tablename__ = "resource"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, description="物资唯一编码")
    type: str = Field(index=True, description="物资分类：主材/辅材/机械/人工")
    name: str = Field(index=True, description="物资名称")
    spec: Optional[str] = Field(default=None, description="物资型号规格")
    measurement_unit: str = Field(description="物资计量单位")
    consumption: Optional[float] = Field(default=None, description="物资定额消耗量")
    description: Optional[str] = Field(default=None, description="物资特性说明、使用要求")
    tags: Optional[str] = Field(default=None, description="多标签逗号分隔")
    is_deleted: int = Field(default=0, description="软删除标记：0=未删除，1=已删除")
    created_at: datetime = Field(default_factory=datetime.now, description="数据创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="数据最后修改时间")
