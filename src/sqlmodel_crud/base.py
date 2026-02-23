"""
CRUD 基础模块

提供通用的 CRUD 基类，支持通过继承方式快速为新实体模型添加基础操作。
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, Union
from sqlmodel import Session, SQLModel, select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import NotFoundError, DatabaseError, ValidationError
from .types import ModelType, CreateSchemaType, UpdateSchemaType, FilterDict


class SoftDeleteMixin:
    """软删除功能 Mixin 类

    提供软删除相关的公共方法，可被 CRUDBase 和 AsyncCRUDBase 复用。
    通过检查模型的 is_deleted 或 deleted_at 字段来判断是否支持软删除。

    示例:
        >>> class MyCRUD(CRUDBase, SoftDeleteMixin):
        ...     pass
    """

    model: Type[SQLModel]

    def _has_soft_delete_fields(self) -> bool:
        """检查模型是否有软删除字段

        检查模型是否包含 is_deleted 或 deleted_at 字段，
        用于判断是否支持软删除功能。

        Returns:
            如果模型有软删除字段返回 True，否则返回 False

        示例:
            >>> if self._has_soft_delete_fields():
            ...     # 执行软删除相关操作
        """
        return hasattr(self.model, "is_deleted") or hasattr(self.model, "deleted_at")

    def _apply_soft_delete_filter(self, statement):
        """应用软删除过滤条件

        如果模型支持软删除，自动添加过滤条件排除已删除的记录。
        优先使用 deleted_at 字段，如果不存在则使用 is_deleted 字段。

        Args:
            statement: SQLAlchemy 查询语句

        Returns:
            添加了软删除过滤条件的查询语句

        示例:
            >>> statement = select(self.model)
            >>> statement = self._apply_soft_delete_filter(statement)
        """
        if not self._has_soft_delete_fields():
            return statement

        # 优先使用 deleted_at 字段（时间戳方式）
        if hasattr(self.model, "deleted_at"):
            statement = statement.where(self.model.deleted_at.is_(None))
        # 否则使用 is_deleted 字段（布尔方式）
        elif hasattr(self.model, "is_deleted"):
            statement = statement.where(
                (self.model.is_deleted == False) | (self.model.is_deleted.is_(None))
            )

        return statement


class RestoreMixin(SoftDeleteMixin):
    """软删除恢复功能 Mixin 类

    为支持软删除的 CRUD 类提供恢复软删除记录的功能。
    继承自 SoftDeleteMixin，复用软删除相关方法。

    示例:
        >>> class UserCRUD(CRUDBase, RestoreMixin):
        ...     pass
        >>>
        >>> # 恢复软删除的用户
        >>> restored_user = user_crud.restore(session, user_id)
    """

    model: Type[SQLModel]

    def restore(self, session: Session, id: Any) -> ModelType:
        """恢复软删除的记录

        将已软删除的记录恢复为正常状态，重置 is_deleted 和 deleted_at 字段。

        Args:
            session: 数据库会话
            id: 记录的主键 ID

        Returns:
            恢复后的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            ValidationError: 模型不支持软删除时抛出

        示例:
            >>> try:
            ...     user = crud.restore(session, 1)
            ...     print(f"已恢复用户: {user.name}")
            ... except NotFoundError:
            ...     print("用户不存在")
        """
        # 检查模型是否支持软删除
        if not self._has_soft_delete_fields():
            raise ValidationError(
                f"模型 {self.model.__name__} 不支持软删除，"
                "缺少 is_deleted 或 deleted_at 字段"
            )

        # 获取记录（包括已软删除的）
        primary_key_column = self.model.__table__.primary_key.columns[0].name
        statement = select(self.model).where(
            getattr(self.model, primary_key_column) == id
        )
        db_obj = session.execute(statement).scalar_one_or_none()

        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        # 恢复记录（根据存在的字段进行恢复）
        if hasattr(self.model, "is_deleted"):
            db_obj.is_deleted = False
        if hasattr(self.model, "deleted_at"):
            db_obj.deleted_at = None

        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)

        return db_obj


class AsyncRestoreMixin(SoftDeleteMixin):
    """异步软删除恢复功能 Mixin 类

    为支持软删除的异步 CRUD 类提供恢复软删除记录的功能。
    继承自 SoftDeleteMixin，复用软删除相关方法。

    示例:
        >>> class UserCRUD(AsyncCRUDBase, AsyncRestoreMixin):
        ...     pass
        >>>
        >>> # 异步恢复软删除的用户
        >>> restored_user = await user_crud.restore(session, user_id)
    """

    model: Type[SQLModel]

    async def restore(self, session: AsyncSession, id: Any) -> ModelType:
        """异步恢复软删除的记录

        将已软删除的记录恢复为正常状态，重置 is_deleted 和 deleted_at 字段。

        Args:
            session: 异步数据库会话
            id: 记录的主键 ID

        Returns:
            恢复后的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            ValidationError: 模型不支持软删除时抛出

        示例:
            >>> try:
            ...     user = await crud.restore(session, 1)
            ...     print(f"已恢复用户: {user.name}")
            ... except NotFoundError:
            ...     print("用户不存在")
        """
        # 检查模型是否支持软删除
        if not self._has_soft_delete_fields():
            raise ValidationError(
                f"模型 {self.model.__name__} 不支持软删除，"
                "缺少 is_deleted 或 deleted_at 字段"
            )

        # 获取记录（包括已软删除的）
        primary_key_column = self.model.__table__.primary_key.columns[0].name
        statement = select(self.model).where(
            getattr(self.model, primary_key_column) == id
        )
        result = await session.execute(statement)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        # 恢复记录（根据存在的字段进行恢复）
        if hasattr(self.model, "is_deleted"):
            db_obj.is_deleted = False
        if hasattr(self.model, "deleted_at"):
            db_obj.deleted_at = None

        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)

        return db_obj


class CRUDBase(SoftDeleteMixin, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """CRUD 基础类

    提供通用的 CRUD 操作实现，支持通过泛型参数绑定任意 SQLModel 模型。
    开发者可以通过继承此类并指定模型类型，快速获得完整的数据库操作能力。

    类型参数:
        ModelType: SQLModel 实体模型类
        CreateSchemaType: 创建操作的数据验证模型
        UpdateSchemaType: 更新操作的数据验证模型

    示例:
        >>> class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
        ...     def __init__(self):
        ...         super().__init__(User)
        ...
        >>> user_crud = UserCRUD()
        >>> user = user_crud.create(session, UserCreate(name="张三"))
    """

    def __init__(self, model: Type[ModelType]):
        """初始化 CRUD 实例

        Args:
            model: SQLModel 实体模型类
        """
        self.model = model

    def get(self, session: Session, id: Any) -> Optional[ModelType]:
        """根据 ID 获取单条记录

        根据主键 ID 查询记录，如果记录不存在或已被软删除则返回 None。

        Args:
            session: 数据库会话
            id: 记录的主键 ID

        Returns:
            查询到的记录对象，不存在或已软删除时返回 None

        Raises:
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> user = crud.get(session, 1)
            >>> if user:
            ...     print(f"找到用户: {user.name}")
        """
        try:
            # 获取主键字段名
            primary_key_column = self.model.__table__.primary_key.columns[0].name

            # 构建查询语句
            statement = select(self.model).where(
                getattr(self.model, primary_key_column) == id
            )

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 执行查询
            result = session.execute(statement).scalar_one_or_none()
            return result
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录失败",
                original=e,
                operation="get",
            )

    def get_or_raise(self, session: Session, id: Any) -> ModelType:
        """根据 ID 获取单条记录，不存在时抛出异常

        与 get 方法类似，但当记录不存在时会抛出 NotFoundError。

        Args:
            session: 数据库会话
            id: 记录的主键 ID

        Returns:
            查询到的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> try:
            ...     user = crud.get_or_raise(session, 1)
            ... except NotFoundError:
            ...     print("用户不存在")
        """
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
        """获取多条记录

        支持分页、过滤和排序功能。

        Args:
            session: 数据库会话
            skip: 跳过的记录数（用于分页）
            limit: 返回的最大记录数
            filters: 过滤条件字典，键为字段名，值为过滤值
            order_by: 排序规则，格式 [("field", "asc"|"desc"), ...]

        Returns:
            记录对象列表

        Raises:
            ValidationError: 参数验证失败时抛出
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> # 获取前10条记录
            >>> users = crud.get_multi(session, limit=10)
            >>>
            >>> # 按条件过滤并分页
            >>> users = crud.get_multi(
            ...     session,
            ...     skip=20,
            ...     limit=10,
            ...     filters={"is_active": True},
            ...     order_by=[("created_at", "desc")]
            ... )
        """
        # 参数验证
        if skip < 0:
            raise ValidationError("skip 不能为负数", field="skip")
        if limit < 0:
            raise ValidationError("limit 不能为负数", field="limit")
        if limit > 1000:
            raise ValidationError("limit 不能超过 1000", field="limit")

        try:
            # 构建基础查询
            statement = select(self.model)

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 应用过滤条件
            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            # 应用排序
            if order_by:
                for field_name, direction in order_by:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if direction.lower() == "desc":
                            statement = statement.order_by(field.desc())
                        else:
                            statement = statement.order_by(field.asc())

            # 应用分页
            statement = statement.offset(skip).limit(limit)

            # 执行查询
            results = session.execute(statement).scalars().all()
            return list(results)

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录列表失败",
                original=e,
                operation="get_multi",
            )

    def create(
        self, session: Session, obj_in: Union[CreateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """创建新记录

        根据传入的数据创建新记录并提交到数据库。

        Args:
            session: 数据库会话
            obj_in: 创建数据，可以是 Pydantic 模型或字典

        Returns:
            创建成功的记录对象

        Raises:
            ValidationError: 数据验证失败时抛出
            DatabaseError: 数据库操作失败时抛出

        示例:
            >>> # 使用 Pydantic 模型
            >>> user = crud.create(session, UserCreate(name="张三", email="zhang@example.com"))
            >>>
            >>> # 使用字典
            >>> user = crud.create(session, {"name": "李四", "email": "li@example.com"})
        """
        try:
            # 转换输入数据为字典
            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)

            # 创建模型实例
            db_obj = self.model(**obj_data)

            # 添加到会话并提交
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                f"创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create",
            )

    def create_multi(
        self,
        session: Session,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
        batch_size: Optional[int] = None,
    ) -> List[ModelType]:
        """批量创建记录

        一次性创建多条记录，使用批量插入提高效率。
        支持分批处理，避免一次性插入大量数据导致内存或性能问题。

        Args:
            session: 数据库会话
            objs_in: 创建数据列表
            batch_size: 每批插入的记录数，默认为 1000

        Returns:
            创建成功的记录对象列表

        Raises:
            ValidationError: 数据验证失败时抛出
            DatabaseError: 数据库操作失败时抛出

        示例:
            >>> # 批量创建，使用默认批次大小
            >>> users = crud.create_multi(session, [
            ...     UserCreate(name="张三", email="zhang@example.com"),
            ...     UserCreate(name="李四", email="li@example.com"),
            ... ])
            >>>
            >>> # 指定批次大小
            >>> users = crud.create_multi(session, user_list, batch_size=500)
        """
        # 如果输入为空，直接返回空列表
        if not objs_in:
            return []

        # 设置默认批次大小
        if batch_size is None:
            batch_size = 1000

        all_db_objs: List[ModelType] = []

        try:
            # 将输入数据分批处理
            for i in range(0, len(objs_in), batch_size):
                batch = objs_in[i : i + batch_size]
                batch_objs: List[ModelType] = []

                # 转换当前批次的数据并创建模型实例
                for obj_in in batch:
                    if isinstance(obj_in, dict):
                        obj_data = obj_in
                    else:
                        obj_data = obj_in.model_dump(exclude_unset=True)

                    db_obj = self.model(**obj_data)
                    batch_objs.append(db_obj)

                # 批量添加当前批次到会话并提交
                session.add_all(batch_objs)
                session.commit()

                # 刷新当前批次的所有对象
                for db_obj in batch_objs:
                    session.refresh(db_obj)

                # 收集创建的对象
                all_db_objs.extend(batch_objs)

            return all_db_objs

        except IntegrityError:
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                f"批量创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create_multi",
            )

    def update(
        self, session: Session, id: Any, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """更新记录

        根据 ID 更新记录，支持部分更新。

        Args:
            session: 数据库会话
            id: 记录的主键 ID
            obj_in: 更新数据，可以是 Pydantic 模型或字典

        Returns:
            更新后的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            ValidationError: 数据验证失败时抛出
            DatabaseError: 数据库操作失败时抛出

        示例:
            >>> # 更新用户名称
            >>> user = crud.update(session, 1, {"name": "新名称"})
            >>>
            >>> # 使用 Pydantic 模型
            >>> user = crud.update(session, 1, UserUpdate(name="新名称"))
        """
        # 获取现有记录
        db_obj = self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:
            # 转换输入数据为字典
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                # exclude_unset=True 只包含显式设置的字段，支持部分更新
                update_data = obj_in.model_dump(exclude_unset=True)

            # 更新对象属性
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # 提交更改
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            session.rollback()
            raise
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                f"更新 {self.model.__name__} 记录失败",
                original=e,
                operation="update",
            )

    def delete(self, session: Session, id: Any, soft: bool = False) -> ModelType:
        """删除记录

        根据 ID 删除记录，支持软删除和硬删除。

        Args:
            session: 数据库会话
            id: 记录的主键 ID
            soft: 是否执行软删除，默认为 False（硬删除）
                  软删除需要模型有 is_deleted 和 deleted_at 字段

        Returns:
            被删除的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            DatabaseError: 数据库操作失败时抛出
            ValidationError: 软删除时模型不支持软删除字段时抛出

        示例:
            >>> # 硬删除（默认）
            >>> deleted_user = crud.delete(session, 1)
            >>> print(f"已删除用户: {deleted_user.name}")
            >>>
            >>> # 软删除
            >>> deleted_user = crud.delete(session, 1, soft=True)
            >>> print(f"已软删除用户: {deleted_user.name}")
        """
        # 获取现有记录
        db_obj = self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:
            if soft:
                # 软删除：检查模型是否支持软删除
                if not self._has_soft_delete_fields():
                    raise ValidationError(
                        f"模型 {self.model.__name__} 不支持软删除，"
                        "缺少 is_deleted 或 deleted_at 字段"
                    )

                # 设置软删除标记（优先使用 deleted_at，其次使用 is_deleted）
                if hasattr(self.model, "deleted_at"):
                    db_obj.deleted_at = datetime.now(timezone.utc)
                if hasattr(self.model, "is_deleted"):
                    db_obj.is_deleted = True

                session.add(db_obj)
                session.commit()
                session.refresh(db_obj)
            else:
                # 硬删除
                session.delete(db_obj)
                session.commit()

            return db_obj

        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                f"删除 {self.model.__name__} 记录失败",
                original=e,
                operation="delete",
            )

    def count(self, session: Session, filters: Optional[FilterDict] = None) -> int:
        """统计记录数

        统计符合条件的记录总数，支持过滤条件。

        Args:
            session: 数据库会话
            filters: 过滤条件字典

        Returns:
            符合条件的记录总数

        Raises:
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> # 统计所有记录
            >>> total = crud.count(session)
            >>>
            >>> # 统计符合条件的记录
            >>> active_count = crud.count(session, filters={"is_active": True})
        """
        try:
            # 构建计数查询
            statement = select(func.count()).select_from(self.model)

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 应用过滤条件
            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            # 执行查询
            result = session.execute(statement).scalar()
            return result or 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"统计 {self.model.__name__} 记录数失败",
                original=e,
                operation="count",
            )

    def exists(self, session: Session, id: Any) -> bool:
        """检查记录是否存在

        根据 ID 检查记录是否存在，比 get 方法更高效。

        Args:
            session: 数据库会话
            id: 记录的主键 ID

        Returns:
            记录存在返回 True，否则返回 False

        Raises:
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> if crud.exists(session, 1):
            ...     print("用户存在")
            ... else:
            ...     print("用户不存在")
        """
        try:
            # 获取主键字段名
            primary_key_column = self.model.__table__.primary_key.columns[0]

            # 构建存在性查询
            statement = select(func.count()).select_from(self.model)
            statement = statement.where(primary_key_column == id)

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 执行查询
            result = session.execute(statement).scalar()
            return (result or 0) > 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"检查 {self.model.__name__} 记录存在性失败",
                original=e,
                operation="exists",
            )


class AsyncCRUDBase(
    SoftDeleteMixin, Generic[ModelType, CreateSchemaType, UpdateSchemaType]
):
    """异步 CRUD 基础类

    提供通用的异步 CRUD 操作实现，支持通过泛型参数绑定任意 SQLModel 模型。
    开发者可以通过继承此类并指定模型类型，快速获得完整的异步数据库操作能力。

    类型参数:
        ModelType: SQLModel 实体模型类
        CreateSchemaType: 创建操作的数据验证模型
        UpdateSchemaType: 更新操作的数据验证模型

    示例:
        >>> class UserCRUD(AsyncCRUDBase[User, UserCreate, UserUpdate]):
        ...     def __init__(self):
        ...         super().__init__(User)
        ...
        >>> user_crud = UserCRUD()
        >>> user = await user_crud.create(session, UserCreate(name="张三"))
    """

    def __init__(self, model: Type[ModelType]):
        """初始化异步 CRUD 实例

        Args:
            model: SQLModel 实体模型类
        """
        self.model = model

    async def get(self, session: AsyncSession, id: Any) -> Optional[ModelType]:
        """根据 ID 获取单条记录

        根据主键 ID 查询记录，如果记录不存在或已被软删除则返回 None。

        Args:
            session: 异步数据库会话
            id: 记录的主键 ID

        Returns:
            查询到的记录对象，不存在或已软删除时返回 None

        Raises:
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> user = await crud.get(session, 1)
            >>> if user:
            ...     print(f"找到用户: {user.name}")
        """
        try:
            # 获取主键字段名
            primary_key_column = self.model.__table__.primary_key.columns[0].name

            # 构建查询语句
            statement = select(self.model).where(
                getattr(self.model, primary_key_column) == id
            )

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 执行查询
            result = await session.execute(statement)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"查询 {self.model.__name__} 记录失败",
                original=e,
                operation="get",
            )

    async def get_or_raise(self, session: AsyncSession, id: Any) -> ModelType:
        """根据 ID 获取单条记录，不存在时抛出异常

        与 get 方法类似，但当记录不存在时会抛出 NotFoundError。

        Args:
            session: 异步数据库会话
            id: 记录的主键 ID

        Returns:
            查询到的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> try:
            ...     user = await crud.get_or_raise(session, 1)
            ... except NotFoundError:
            ...     print("用户不存在")
        """
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
        """获取多条记录

        支持分页、过滤和排序功能。

        Args:
            session: 异步数据库会话
            skip: 跳过的记录数（用于分页）
            limit: 返回的最大记录数
            filters: 过滤条件字典，键为字段名，值为过滤值
            order_by: 排序规则，格式 [("field", "asc"|"desc"), ...]

        Returns:
            记录对象列表

        Raises:
            ValidationError: 参数验证失败时抛出
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> # 获取前10条记录
            >>> users = await crud.get_multi(session, limit=10)
            >>>
            >>> # 按条件过滤并分页
            >>> users = await crud.get_multi(
            ...     session,
            ...     skip=20,
            ...     limit=10,
            ...     filters={"is_active": True},
            ...     order_by=[("created_at", "desc")]
            ... )
        """
        # 参数验证
        if skip < 0:
            raise ValidationError("skip 不能为负数", field="skip")
        if limit < 0:
            raise ValidationError("limit 不能为负数", field="limit")
        if limit > 1000:
            raise ValidationError("limit 不能超过 1000", field="limit")

        try:
            # 构建基础查询
            statement = select(self.model)

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 应用过滤条件
            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            # 应用排序
            if order_by:
                for field_name, direction in order_by:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if direction.lower() == "desc":
                            statement = statement.order_by(field.desc())
                        else:
                            statement = statement.order_by(field.asc())

            # 应用分页
            statement = statement.offset(skip).limit(limit)

            # 执行查询
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
        self, session: AsyncSession, obj_in: Union[CreateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """创建新记录

        根据传入的数据创建新记录并提交到数据库。

        Args:
            session: 异步数据库会话
            obj_in: 创建数据，可以是 Pydantic 模型或字典

        Returns:
            创建成功的记录对象

        Raises:
            ValidationError: 数据验证失败时抛出
            DatabaseError: 数据库操作失败时抛出

        示例:
            >>> # 使用 Pydantic 模型
            >>> user = await crud.create(session, UserCreate(name="张三", email="zhang@example.com"))
            >>>
            >>> # 使用字典
            >>> user = await crud.create(session, {"name": "李四", "email": "li@example.com"})
        """
        try:
            # 转换输入数据为字典
            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)

            # 创建模型实例
            db_obj = self.model(**obj_data)

            # 添加到会话并提交
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(
                f"创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create",
            )

    async def create_multi(
        self,
        session: AsyncSession,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
        batch_size: Optional[int] = None,
    ) -> List[ModelType]:
        """批量创建记录

        一次性创建多条记录，使用批量插入提高效率。
        支持分批处理，避免一次性插入过多数据导致内存问题。

        Args:
            session: 异步数据库会话
            objs_in: 创建数据列表
            batch_size: 每批处理的记录数，默认为 1000

        Returns:
            创建成功的记录对象列表

        Raises:
            ValidationError: 数据验证失败时抛出
            DatabaseError: 数据库操作失败时抛出

        示例:
            >>> # 批量创建
            >>> users = await crud.create_multi(session, [
            ...     UserCreate(name="张三", email="zhang@example.com"),
            ...     UserCreate(name="李四", email="li@example.com"),
            ... ])
            >>>
            >>> # 自定义批次大小
            >>> users = await crud.create_multi(session, user_list, batch_size=500)
        """
        if not objs_in:
            return []

        # 设置默认批次大小
        if batch_size is None:
            batch_size = 1000

        all_db_objs: List[ModelType] = []

        try:
            # 分批处理
            for i in range(0, len(objs_in), batch_size):
                batch = objs_in[i : i + batch_size]
                db_objs = []

                for obj_in in batch:
                    # 转换输入数据为字典
                    if isinstance(obj_in, dict):
                        obj_data = obj_in
                    else:
                        obj_data = obj_in.model_dump(exclude_unset=True)

                    # 创建模型实例
                    db_obj = self.model(**obj_data)
                    db_objs.append(db_obj)

                # 批量添加到会话并提交
                session.add_all(db_objs)
                await session.commit()

                # 刷新所有对象
                for db_obj in db_objs:
                    await session.refresh(db_obj)

                all_db_objs.extend(db_objs)

            return all_db_objs

        except IntegrityError:
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(
                f"批量创建 {self.model.__name__} 记录失败",
                original=e,
                operation="create_multi",
            )

    async def update(
        self,
        session: AsyncSession,
        id: Any,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """更新记录

        根据 ID 更新记录，支持部分更新。

        Args:
            session: 异步数据库会话
            id: 记录的主键 ID
            obj_in: 更新数据，可以是 Pydantic 模型或字典

        Returns:
            更新后的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            ValidationError: 数据验证失败时抛出
            DatabaseError: 数据库操作失败时抛出

        示例:
            >>> # 更新用户名称
            >>> user = await crud.update(session, 1, {"name": "新名称"})
            >>>
            >>> # 使用 Pydantic 模型
            >>> user = await crud.update(session, 1, UserUpdate(name="新名称"))
        """
        # 获取现有记录
        db_obj = await self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:
            # 转换输入数据为字典
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                # exclude_unset=True 只包含显式设置的字段，支持部分更新
                update_data = obj_in.model_dump(exclude_unset=True)

            # 更新对象属性
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # 提交更改
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)

            return db_obj

        except IntegrityError:
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(
                f"更新 {self.model.__name__} 记录失败",
                original=e,
                operation="update",
            )

    async def delete(
        self, session: AsyncSession, id: Any, soft: bool = False
    ) -> ModelType:
        """删除记录

        根据 ID 删除记录，支持软删除和硬删除。

        Args:
            session: 异步数据库会话
            id: 记录的主键 ID
            soft: 是否执行软删除，默认为 False（硬删除）
                  软删除需要模型有 is_deleted 和 deleted_at 字段

        Returns:
            被删除的记录对象

        Raises:
            NotFoundError: 记录不存在时抛出
            DatabaseError: 数据库操作失败时抛出
            ValidationError: 软删除时模型不支持软删除字段时抛出

        示例:
            >>> # 硬删除（默认）
            >>> deleted_user = await crud.delete(session, 1)
            >>> print(f"已删除用户: {deleted_user.name}")
            >>>
            >>> # 软删除
            >>> deleted_user = await crud.delete(session, 1, soft=True)
            >>> print(f"已软删除用户: {deleted_user.name}")
        """
        # 获取现有记录
        db_obj = await self.get(session, id)
        if db_obj is None:
            raise NotFoundError(resource=self.model.__name__, identifier=id)

        try:
            if soft:
                # 软删除：检查模型是否支持软删除
                if not self._has_soft_delete_fields():
                    raise ValidationError(
                        f"模型 {self.model.__name__} 不支持软删除，"
                        "缺少 is_deleted 或 deleted_at 字段"
                    )

                # 设置软删除标记（优先使用 deleted_at，其次使用 is_deleted）
                if hasattr(self.model, "deleted_at"):
                    db_obj.deleted_at = datetime.now(timezone.utc)
                if hasattr(self.model, "is_deleted"):
                    db_obj.is_deleted = True

                session.add(db_obj)
                await session.commit()
                await session.refresh(db_obj)
            else:
                # 硬删除
                await session.delete(db_obj)
                await session.commit()

            return db_obj

        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(
                f"删除 {self.model.__name__} 记录失败",
                original=e,
                operation="delete",
            )

    async def count(
        self, session: AsyncSession, filters: Optional[FilterDict] = None
    ) -> int:
        """统计记录数

        统计符合条件的记录总数，支持过滤条件。

        Args:
            session: 异步数据库会话
            filters: 过滤条件字典

        Returns:
            符合条件的记录总数

        Raises:
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> # 统计所有记录
            >>> total = await crud.count(session)
            >>>
            >>> # 统计符合条件的记录
            >>> active_count = await crud.count(session, filters={"is_active": True})
        """
        try:
            # 构建计数查询
            statement = select(func.count()).select_from(self.model)

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 应用过滤条件
            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        statement = statement.where(field == value)

            # 执行查询
            result = await session.execute(statement)
            return result.scalar() or 0

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"统计 {self.model.__name__} 记录数失败",
                original=e,
                operation="count",
            )

    async def exists(self, session: AsyncSession, id: Any) -> bool:
        """检查记录是否存在

        根据 ID 检查记录是否存在，比 get 方法更高效。

        Args:
            session: 异步数据库会话
            id: 记录的主键 ID

        Returns:
            记录存在返回 True，否则返回 False

        Raises:
            DatabaseError: 数据库查询失败时抛出

        示例:
            >>> if await crud.exists(session, 1):
            ...     print("用户存在")
            ... else:
            ...     print("用户不存在")
        """
        try:
            # 获取主键字段名
            primary_key_column = self.model.__table__.primary_key.columns[0]

            # 构建存在性查询
            statement = select(func.count()).select_from(self.model)
            statement = statement.where(primary_key_column == id)

            # 应用软删除过滤
            statement = self._apply_soft_delete_filter(statement)

            # 执行查询
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
