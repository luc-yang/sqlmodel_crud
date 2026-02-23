# coding:utf-8
"""
数据层统一导出模块

导出数据层的所有公开接口，包括：
- 配置管理
- 数据库初始化
- 数据模型
- CRUD 仓库

该文件由 SQLModel CRUD 生成器自动生成。

生成时间: 2026-02-23 21:15:42
警告: 请勿手动修改此文件，你的更改可能会在下次生成时被覆盖。
"""

# 配置
from .config import DatabaseConfig, default_config

# 数据库初始化
from .database import DatabaseInitializer, init_database, DatabaseManager, db

# 数据模型和 CRUD
# ConstructionQuantity 相关
from .models.construction_quantity import ConstructionQuantity
from .crud.construction_quantity import ConstructionQuantityCRUD
# DivisionalWork 相关
from .models.divisional_work import DivisionalWork
from .crud.divisional_work import DivisionalWorkCRUD
# Location 相关
from .models.location import Location
from .crud.location import LocationCRUD
# Quota 相关
from .models.quota import Quota
from .crud.quota import QuotaCRUD
# Resource 相关
from .models.resource import Resource
from .crud.resource import ResourceCRUD
# UnitProject 相关
from .models.unit_project import UnitProject
from .crud.unit_project import UnitProjectCRUD
# User 相关
from .models.user import User
from .crud.user import UserCRUD


__all__ = [
    # 配置
    "DatabaseConfig",
    "default_config",
    # 数据库初始化
    "DatabaseInitializer",
    "init_database",
    "DatabaseManager",
    "db",
    # ConstructionQuantity 模型
    "ConstructionQuantity",
    "ConstructionQuantityCRUD",
    # DivisionalWork 模型
    "DivisionalWork",
    "DivisionalWorkCRUD",
    # Location 模型
    "Location",
    "LocationCRUD",
    # Quota 模型
    "Quota",
    "QuotaCRUD",
    # Resource 模型
    "Resource",
    "ResourceCRUD",
    # UnitProject 模型
    "UnitProject",
    "UnitProjectCRUD",
    # User 模型
    "User",
    "UserCRUD",
]
