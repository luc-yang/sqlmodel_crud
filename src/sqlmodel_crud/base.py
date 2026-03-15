"""CRUD 基础模块"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, Union
from sqlmodel import Session, SQLModel, select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import NotFoundError, DatabaseError, ValidationError
from .types import ModelType, CreateInputType, UpdateInputType, FilterDict


class SoftDeleteMixin:
    """软删除功能 Mixin 类"""

    model: Type[SQLModel]

    def _has_soft_delete_fields(self) -> bool:
        """检查模型是否有软删除字段"""
        return hasattr(self.model, "is_deleted") or hasattr(self.model, "deleted_at")

    def _apply_soft_delete_filter(self, statement):
        """应用软删除过滤条件"""
        if not self._has_soft_delete_fields():
            return statement

        if hasattr(self.model, "deleted_at"):
            statement = statement.where(self.model.deleted_at.is_(None))

        elif hasattr(self.model, "is_deleted"):
            statement = statement.where(
                (self.model.is_deleted == False) | (self.model.is_deleted.is_(None))
            )

        return statement


class RestoreMixin(SoftDeleteMixin):
    """软删除恢复功能 Mixin 类"""

    model: Type[SQLModel]

    def restore(self, session: Session, id: Any) -> ModelType:
        """恢复软删除的记录"""

        if not self._has_soft_delete_fields():
            raise ValidationError(
                f"模型 {self.model.__name__} 不支持软删除，"
                "缺少 is_deleted 或 deleted_at 字段"
            )

        primary_key_column = self.model.__table__.primary_key.columns[0].name
        statement = select(self.model).where(
            getattr(self.model, primary_key_column) == id
        )
        db_obj = session.execute(statement).scalar_one_or_none()

        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        if hasattr(self.model, "is_deleted"):
            db_obj.is_deleted = False
        if hasattr(self.model, "deleted_at"):
            db_obj.deleted_at = None

        session.add(db_obj)
        session.flush()
        session.refresh(db_obj)

        return db_obj


class AsyncRestoreMixin(SoftDeleteMixin):
    """异步软删除恢复功能 Mixin 类"""

    model: Type[SQLModel]

    async def restore(self, session: AsyncSession, id: Any) -> ModelType:
        """异步恢复软删除的记录"""

        if not self._has_soft_delete_fields():
            raise ValidationError(
                f"模型 {self.model.__name__} 不支持软删除，"
                "缺少 is_deleted 或 deleted_at 字段"
            )

        primary_key_column = self.model.__table__.primary_key.columns[0].name
        statement = select(self.model).where(
            getattr(self.model, primary_key_column) == id
        )
        result = await session.execute(statement)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        if hasattr(self.model, "is_deleted"):
            db_obj.is_deleted = False
        if hasattr(self.model, "deleted_at"):
            db_obj.deleted_at = None

        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)

        return db_obj


class CRUDBase(SoftDeleteMixin, Generic[ModelType, CreateInputType, UpdateInputType]):
    """CRUD 基础类"""

    def __init__(self, model: Type[ModelType]):
        """初始化 CRUD 实例"""
        self.model = model

    def get(self, session: Session, id: Any) -> Optional[ModelType]:
        """根据 ID 获取单条记录"""
        try:

            primary_key_column = self.model.__table__.primary_key.columns[0].name

            statement = select(self.model).where(
                getattr(self.model, primary_key_column) == id
            )

            statement = self._apply_soft_delete_filter(statement)

            result = session.execute(statement).scalar_one_or_none()
            return result
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录失败",
                original=e,
                operation="get",
            )

    def get_or_raise(self, session: Session, id: Any) -> ModelType:
        """根据 ID 获取单条记录，不存在时抛出异常"""
        obj = self.get(session, id)
        if obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)
        return obj

    def get_multi(
        self,
        session: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[FilterDict] = None,
        order_by: Optional[List[tuple]] = None,
    ) -> List[ModelType]:
        """获取多条记录"""

        if skip < 0:
            raise ValidationError("skip 不能为负数", field="skip")
        if limit < 0:
            raise ValidationError("limit 不能为负数", field="limit")
        if limit > 1000:
            raise ValidationError("limit 不能超过 1000", field="limit")

        try:

            statement = select(self.model)

            statement = self._apply_soft_delete_filter(statement)

            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            if order_by:
                for field_name, direction in order_by:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if direction.lower() == "desc":
                            statement = statement.order_by(field.desc())
                        else:
                            statement = statement.order_by(field.asc())

            statement = statement.offset(skip).limit(limit)

            results = session.execute(statement).scalars().all()
            return list(results)

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录列表失败",
                original=e,
                operation="get_multi",
            )

    def create(
        self, session: Session, obj_in: Union[CreateInputType, Dict[str, Any]]
    ) -> ModelType:
        """创建新记录"""
        try:

            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)

            db_obj = self.model(**obj_data)

            session.add(db_obj)
            session.flush()
            session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create",
            )

    def create_multi(
        self,
        session: Session,
        objs_in: List[Union[CreateInputType, Dict[str, Any]]],
        batch_size: Optional[int] = None,
    ) -> List[ModelType]:
        """批量创建记录"""

        if not objs_in:
            return []

        if batch_size is None:
            batch_size = 1000

        all_db_objs: List[ModelType] = []

        try:

            for i in range(0, len(objs_in), batch_size):
                batch = objs_in[i : i + batch_size]
                batch_objs: List[ModelType] = []

                for obj_in in batch:
                    if isinstance(obj_in, dict):
                        obj_data = obj_in
                    else:
                        obj_data = obj_in.model_dump(exclude_unset=True)

                    db_obj = self.model(**obj_data)
                    batch_objs.append(db_obj)

                session.add_all(batch_objs)
                session.flush()

                for db_obj in batch_objs:
                    session.refresh(db_obj)

                all_db_objs.extend(batch_objs)

            return all_db_objs

        except IntegrityError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"批量创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create_multi",
            )

    def update(
        self, session: Session, id: Any, obj_in: Union[UpdateInputType, Dict[str, Any]]
    ) -> ModelType:
        """更新记录"""

        db_obj = self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:

            if isinstance(obj_in, dict):
                update_data = obj_in
            else:

                update_data = obj_in.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            session.add(db_obj)
            session.flush()
            session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"更新 {self.model.__name__} 记录失败",
                original=e,
                operation="update",
            )

    def delete(self, session: Session, id: Any, soft: bool = False) -> ModelType:
        """删除记录"""

        db_obj = self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:
            if soft:

                if not self._has_soft_delete_fields():
                    raise ValidationError(
                        f"模型 {self.model.__name__} 不支持软删除，"
                        "缺少 is_deleted 或 deleted_at 字段"
                    )

                if hasattr(self.model, "deleted_at"):
                    db_obj.deleted_at = datetime.now(timezone.utc)
                if hasattr(self.model, "is_deleted"):
                    db_obj.is_deleted = True

                session.add(db_obj)
                session.flush()
                session.refresh(db_obj)
            else:

                session.delete(db_obj)
                session.flush()

            return db_obj

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"删除 {self.model.__name__} 记录失败",
                original=e,
                operation="delete",
            )

    def count(self, session: Session, filters: Optional[FilterDict] = None) -> int:
        """统计记录数"""
        try:

            statement = select(func.count()).select_from(self.model)

            statement = self._apply_soft_delete_filter(statement)

            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            result = session.execute(statement).scalar()
            return result or 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"统计 {self.model.__name__} 记录数失败",
                original=e,
                operation="count",
            )

    def exists(self, session: Session, id: Any) -> bool:
        """检查记录是否存在"""
        try:

            primary_key_column = self.model.__table__.primary_key.columns[0]

            statement = select(func.count()).select_from(self.model)
            statement = statement.where(primary_key_column == id)

            statement = self._apply_soft_delete_filter(statement)

            result = session.execute(statement).scalar()
            return (result or 0) > 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"检查 {self.model.__name__} 记录存在性失败",
                original=e,
                operation="exists",
            )


class AsyncCRUDBase(
    SoftDeleteMixin, Generic[ModelType, CreateInputType, UpdateInputType]
):
    """异步 CRUD 基础类"""

    def __init__(self, model: Type[ModelType]):
        """初始化异步 CRUD 实例"""
        self.model = model

    async def get(self, session: AsyncSession, id: Any) -> Optional[ModelType]:
        """根据 ID 获取单条记录"""
        try:

            primary_key_column = self.model.__table__.primary_key.columns[0].name

            statement = select(self.model).where(
                getattr(self.model, primary_key_column) == id
            )

            statement = self._apply_soft_delete_filter(statement)

            result = await session.execute(statement)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录失败",
                original=e,
                operation="get",
            )

    async def get_or_raise(self, session: AsyncSession, id: Any) -> ModelType:
        """根据 ID 获取单条记录，不存在时抛出异常"""
        obj = await self.get(session, id)
        if obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)
        return obj

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[FilterDict] = None,
        order_by: Optional[List[tuple]] = None,
    ) -> List[ModelType]:
        """获取多条记录"""

        if skip < 0:
            raise ValidationError("skip 不能为负数", field="skip")
        if limit < 0:
            raise ValidationError("limit 不能为负数", field="limit")
        if limit > 1000:
            raise ValidationError("limit 不能超过 1000", field="limit")

        try:

            statement = select(self.model)

            statement = self._apply_soft_delete_filter(statement)

            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            if order_by:
                for field_name, direction in order_by:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if direction.lower() == "desc":
                            statement = statement.order_by(field.desc())
                        else:
                            statement = statement.order_by(field.asc())

            statement = statement.offset(skip).limit(limit)

            result = await session.execute(statement)
            results = result.scalars().all()
            return list(results)

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录列表失败",
                original=e,
                operation="get_multi",
            )

    async def create(
        self, session: AsyncSession, obj_in: Union[CreateInputType, Dict[str, Any]]
    ) -> ModelType:
        """创建新记录"""
        try:

            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)

            db_obj = self.model(**obj_data)

            session.add(db_obj)
            await session.flush()
            await session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create",
            )

    async def create_multi(
        self,
        session: AsyncSession,
        objs_in: List[Union[CreateInputType, Dict[str, Any]]],
        batch_size: Optional[int] = None,
    ) -> List[ModelType]:
        """批量创建记录"""
        if not objs_in:
            return []

        if batch_size is None:
            batch_size = 1000

        all_db_objs: List[ModelType] = []

        try:

            for i in range(0, len(objs_in), batch_size):
                batch = objs_in[i : i + batch_size]
                db_objs = []

                for obj_in in batch:

                    if isinstance(obj_in, dict):
                        obj_data = obj_in
                    else:
                        obj_data = obj_in.model_dump(exclude_unset=True)

                    db_obj = self.model(**obj_data)
                    db_objs.append(db_obj)

                session.add_all(db_objs)
                await session.flush()

                for db_obj in db_objs:
                    await session.refresh(db_obj)

                all_db_objs.extend(db_objs)

            return all_db_objs

        except IntegrityError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"批量创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create_multi",
            )

    async def update(
        self,
        session: AsyncSession,
        id: Any,
        obj_in: Union[UpdateInputType, Dict[str, Any]],
    ) -> ModelType:
        """更新记录"""

        db_obj = await self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:

            if isinstance(obj_in, dict):
                update_data = obj_in
            else:

                update_data = obj_in.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            session.add(db_obj)
            await session.flush()
            await session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"更新 {self.model.__name__} 记录失败",
                original=e,
                operation="update",
            )

    async def delete(
        self, session: AsyncSession, id: Any, soft: bool = False
    ) -> ModelType:
        """删除记录"""

        db_obj = await self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:
            if soft:

                if not self._has_soft_delete_fields():
                    raise ValidationError(
                        f"模型 {self.model.__name__} 不支持软删除，"
                        "缺少 is_deleted 或 deleted_at 字段"
                    )

                if hasattr(self.model, "deleted_at"):
                    db_obj.deleted_at = datetime.now(timezone.utc)
                if hasattr(self.model, "is_deleted"):
                    db_obj.is_deleted = True

                session.add(db_obj)
                await session.flush()
                await session.refresh(db_obj)
            else:

                await session.delete(db_obj)
                await session.flush()

            return db_obj

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"删除 {self.model.__name__} 记录失败",
                original=e,
                operation="delete",
            )

    async def count(
        self, session: AsyncSession, filters: Optional[FilterDict] = None
    ) -> int:
        """统计记录数"""
        try:

            statement = select(func.count()).select_from(self.model)

            statement = self._apply_soft_delete_filter(statement)

            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            result = await session.execute(statement)
            return result.scalar() or 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"统计 {self.model.__name__} 记录数失败",
                original=e,
                operation="count",
            )

    async def exists(self, session: AsyncSession, id: Any) -> bool:
        """检查记录是否存在"""
        try:

            primary_key_column = self.model.__table__.primary_key.columns[0]

            statement = select(func.count()).select_from(self.model)
            statement = statement.where(primary_key_column == id)

            statement = self._apply_soft_delete_filter(statement)

            result = await session.execute(statement)
            return (result.scalar() or 0) > 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"检查 {self.model.__name__} 记录存在性失败",
                original=e,
                operation="exists",
            )


__all__ = [
    "SoftDeleteMixin",
    "RestoreMixin",
    "AsyncRestoreMixin",
    "CRUDBase",
    "AsyncCRUDBase",
]
