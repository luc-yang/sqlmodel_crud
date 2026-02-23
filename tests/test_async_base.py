"""
AsyncCRUDBase 类测试模块

测试 AsyncCRUDBase 类的所有异步方法，包括：
- get / get_or_404: 单条记录查询
- get_multi: 多条记录查询（支持分页、过滤、排序）
- create: 创建单条记录
- create_multi: 批量创建记录
- update: 更新记录
- delete: 删除记录（支持软删除）
- count: 统计记录数
- exists: 检查记录是否存在
"""

from typing import Optional

import pytest
from pydantic import BaseModel

from sqlmodel_crud.exceptions import NotFoundError, ValidationError

# =============================================================================
# Pydantic 模型定义（用于测试）
# =============================================================================


class UserCreate(BaseModel):
    """用户创建模型"""

    name: str
    email: str
    age: Optional[int] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    """用户更新模型"""

    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    is_active: Optional[bool] = None


# =============================================================================
# TestAsyncCRUDBaseGet - 单条记录查询测试
# =============================================================================


class TestAsyncCRUDBaseGet:
    """测试 AsyncCRUDBase 的单条记录查询方法"""

    async def test_async_get_existing_record(self, async_session, async_test_user_crud):
        """测试异步 get 方法返回存在的记录

        验证：当记录存在时，get 方法应返回该记录对象
        """
        # 创建测试用户
        user = await async_test_user_crud.create(
            async_session, {"name": "张三", "email": "zhang@example.com"}
        )

        # 通过 get 方法获取用户
        result = await async_test_user_crud.get(async_session, user.id)

        # 验证返回结果
        assert result is not None
        assert result.id == user.id
        assert result.name == "张三"
        assert result.email == "zhang@example.com"

    async def test_async_get_nonexistent_record(
        self, async_session, async_test_user_crud
    ):
        """测试异步 get 方法对不存在的 ID 返回 None

        验证：当记录不存在时，get 方法应返回 None
        """
        # 尝试获取不存在的记录
        result = await async_test_user_crud.get(async_session, 99999)

        # 验证返回 None
        assert result is None

    async def test_async_get_or_raise_existing(
        self, async_session, async_test_user_crud
    ):
        """测试异步 get_or_raise 返回存在的记录

        验证：当记录存在时，get_or_raise 方法应返回该记录对象
        """
        # 创建测试用户
        user = await async_test_user_crud.create(
            async_session, {"name": "李四", "email": "li@example.com"}
        )

        # 通过 get_or_raise 方法获取用户
        result = await async_test_user_crud.get_or_raise(async_session, user.id)

        # 验证返回结果
        assert result is not None
        assert result.id == user.id
        assert result.name == "李四"

    async def test_async_get_or_raise_nonexistent(
        self, async_session, async_test_user_crud
    ):
        """测试异步 get_or_raise 对不存在的 ID 抛出 NotFoundError

        验证：当记录不存在时，get_or_raise 方法应抛出 NotFoundError
        """
        # 尝试获取不存在的记录，应抛出 NotFoundError
        with pytest.raises(NotFoundError) as exc_info:
            await async_test_user_crud.get_or_raise(async_session, 99999)

        # 验证异常信息
        assert "TestUser" in str(exc_info.value)
        assert "99999" in str(exc_info.value)


# =============================================================================
# TestAsyncCRUDBaseGetMulti - 多条记录查询测试
# =============================================================================


class TestAsyncCRUDBaseGetMulti:
    """测试 AsyncCRUDBase 的多条记录查询方法"""

    async def test_async_get_multi_basic(self, async_session, async_test_user_crud):
        """测试异步基本查询返回列表

        验证：get_multi 方法应返回记录列表
        """
        # 创建多个测试用户
        await async_test_user_crud.create(
            async_session, {"name": "用户1", "email": "user1@test.com"}
        )
        await async_test_user_crud.create(
            async_session, {"name": "用户2", "email": "user2@test.com"}
        )
        await async_test_user_crud.create(
            async_session, {"name": "用户3", "email": "user3@test.com"}
        )

        # 获取所有用户
        results = await async_test_user_crud.get_multi(async_session)

        # 验证返回结果
        assert len(results) == 3
        assert all(hasattr(user, "name") for user in results)

    async def test_async_get_multi_pagination(
        self, async_session, async_test_user_crud
    ):
        """测试异步 skip 和 limit 分页功能

        验证：skip 和 limit 参数应正确实现分页
        """
        # 创建 5 个测试用户
        for i in range(5):
            await async_test_user_crud.create(
                async_session, {"name": f"用户{i}", "email": f"user{i}@test.com"}
            )

        # 测试 skip 参数
        results_skip = await async_test_user_crud.get_multi(async_session, skip=2)
        assert len(results_skip) == 3

        # 测试 limit 参数
        results_limit = await async_test_user_crud.get_multi(async_session, limit=2)
        assert len(results_limit) == 2

        # 测试 skip 和 limit 组合
        results_both = await async_test_user_crud.get_multi(
            async_session, skip=1, limit=2
        )
        assert len(results_both) == 2

    async def test_async_get_multi_filters(self, async_session, async_test_user_crud):
        """测试异步 filters 过滤功能

        验证：filters 参数应正确过滤记录
        """
        # 创建不同状态的用户
        await async_test_user_crud.create(
            async_session,
            {"name": "活跃用户1", "email": "active1@test.com", "is_active": True},
        )
        await async_test_user_crud.create(
            async_session,
            {"name": "活跃用户2", "email": "active2@test.com", "is_active": True},
        )
        await async_test_user_crud.create(
            async_session,
            {"name": "非活跃用户", "email": "inactive@test.com", "is_active": False},
        )

        # 过滤活跃用户
        active_users = await async_test_user_crud.get_multi(
            async_session, filters={"is_active": True}
        )
        assert len(active_users) == 2
        assert all(user.is_active for user in active_users)

        # 过滤非活跃用户
        inactive_users = await async_test_user_crud.get_multi(
            async_session, filters={"is_active": False}
        )
        assert len(inactive_users) == 1
        assert not inactive_users[0].is_active

    async def test_async_get_multi_order_by(self, async_session, async_test_user_crud):
        """测试异步 order_by 排序功能

        验证：order_by 参数应正确排序记录
        """
        # 创建测试用户（按特定顺序）
        await async_test_user_crud.create(
            async_session, {"name": "张三", "email": "zhang@test.com", "age": 30}
        )
        await async_test_user_crud.create(
            async_session, {"name": "李四", "email": "li@test.com", "age": 25}
        )
        await async_test_user_crud.create(
            async_session, {"name": "王五", "email": "wang@test.com", "age": 35}
        )

        # 按年龄升序排序
        results_asc = await async_test_user_crud.get_multi(
            async_session, order_by=[("age", "asc")]
        )
        ages_asc = [user.age for user in results_asc]
        assert ages_asc == [25, 30, 35]

        # 按年龄降序排序
        results_desc = await async_test_user_crud.get_multi(
            async_session, order_by=[("age", "desc")]
        )
        ages_desc = [user.age for user in results_desc]
        assert ages_desc == [35, 30, 25]

    async def test_async_get_multi_negative_skip_raises_error(
        self, async_session, async_test_user_crud
    ):
        """测试异步负数 skip 抛出 ValidationError

        验证：当 skip 为负数时，应抛出 ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            await async_test_user_crud.get_multi(async_session, skip=-1)

        assert "skip" in str(exc_info.value)

    async def test_async_get_multi_negative_limit_raises_error(
        self, async_session, async_test_user_crud
    ):
        """测试异步负数 limit 抛出 ValidationError

        验证：当 limit 为负数时，应抛出 ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            await async_test_user_crud.get_multi(async_session, limit=-1)

        assert "limit" in str(exc_info.value)


# =============================================================================
# TestAsyncCRUDBaseCreate - 创建记录测试
# =============================================================================


class TestAsyncCRUDBaseCreate:
    """测试 AsyncCRUDBase 的创建记录方法"""

    async def test_async_create_with_dict(self, async_session, async_test_user_crud):
        """测试异步使用字典创建记录

        验证：可以使用字典数据创建记录
        """
        # 使用字典创建用户
        user_data = {"name": "字典用户", "email": "dict@test.com", "age": 25}
        user = await async_test_user_crud.create(async_session, user_data)

        # 验证创建结果
        assert user is not None
        assert user.name == "字典用户"
        assert user.email == "dict@test.com"
        assert user.age == 25

    async def test_async_create_with_pydantic_model(
        self, async_session, async_test_user_crud
    ):
        """测试异步使用 Pydantic 模型创建记录

        验证：可以使用 Pydantic 模型创建记录
        """
        # 使用 Pydantic 模型创建用户
        user_data = UserCreate(name="Pydantic用户", email="pydantic@test.com", age=30)
        user = await async_test_user_crud.create(async_session, user_data)

        # 验证创建结果
        assert user is not None
        assert user.name == "Pydantic用户"
        assert user.email == "pydantic@test.com"
        assert user.age == 30

    async def test_async_create_returns_object_with_id(
        self, async_session, async_test_user_crud
    ):
        """测试异步创建后返回的对象有 ID

        验证：创建记录后，返回的对象应包含自动生成的 ID
        """
        # 创建用户
        user = await async_test_user_crud.create(
            async_session, {"name": "ID测试用户", "email": "id@test.com"}
        )

        # 验证 ID 存在且为整数
        assert user.id is not None
        assert isinstance(user.id, int)
        assert user.id > 0


# =============================================================================
# TestAsyncCRUDBaseCreateMulti - 批量创建记录测试
# =============================================================================


class TestAsyncCRUDBaseCreateMulti:
    """测试 AsyncCRUDBase 的批量创建记录方法"""

    async def test_async_create_multi_with_list(
        self, async_session, async_test_user_crud
    ):
        """测试异步批量创建多条记录

        验证：可以一次性创建多条记录
        """
        # 准备批量创建数据
        users_data = [
            {"name": "批量用户1", "email": "batch1@test.com"},
            {"name": "批量用户2", "email": "batch2@test.com"},
            {"name": "批量用户3", "email": "batch3@test.com"},
        ]

        # 批量创建
        users = await async_test_user_crud.create_multi(async_session, users_data)

        # 验证创建结果
        assert len(users) == 3
        assert all(user.id is not None for user in users)
        assert [user.name for user in users] == ["批量用户1", "批量用户2", "批量用户3"]

    async def test_async_create_multi_empty_list(
        self, async_session, async_test_user_crud
    ):
        """测试异步空列表返回空列表

        验证：传入空列表时，应返回空列表
        """
        # 传入空列表
        result = await async_test_user_crud.create_multi(async_session, [])

        # 验证返回空列表
        assert result == []


# =============================================================================
# TestAsyncCRUDBaseUpdate - 更新记录测试
# =============================================================================


class TestAsyncCRUDBaseUpdate:
    """测试 AsyncCRUDBase 的更新记录方法"""

    async def test_async_update_existing_record(
        self, async_session, async_test_user_crud
    ):
        """测试异步更新存在的记录

        验证：可以更新已存在的记录
        """
        # 创建测试用户
        user = await async_test_user_crud.create(
            async_session, {"name": "原名称", "email": "update@test.com", "age": 20}
        )

        # 更新用户
        updated_user = await async_test_user_crud.update(
            async_session, user.id, {"name": "新名称", "age": 30}
        )

        # 验证更新结果
        assert updated_user.name == "新名称"
        assert updated_user.age == 30
        assert updated_user.email == "update@test.com"  # 未更新的字段保持不变

    async def test_async_update_partial(self, async_session, async_test_user_crud):
        """测试异步部分更新（只更新部分字段）

        验证：可以只更新部分字段，其他字段保持不变
        """
        # 创建测试用户
        user = await async_test_user_crud.create(
            async_session,
            {"name": "部分更新测试", "email": "partial@test.com", "age": 25},
        )

        # 只更新名称
        updated_user = await async_test_user_crud.update(
            async_session, user.id, {"name": "仅更新名称"}
        )

        # 验证更新结果
        assert updated_user.name == "仅更新名称"
        assert updated_user.email == "partial@test.com"  # 未改变
        assert updated_user.age == 25  # 未改变

    async def test_async_update_nonexistent_raises_error(
        self, async_session, async_test_user_crud
    ):
        """测试异步更新不存在的记录抛出 NotFoundError

        验证：尝试更新不存在的记录时，应抛出 NotFoundError
        """
        with pytest.raises(NotFoundError) as exc_info:
            await async_test_user_crud.update(
                async_session, 99999, {"name": "不存在的用户"}
            )

        assert "TestUser" in str(exc_info.value)


# =============================================================================
# TestAsyncCRUDBaseDelete - 删除记录测试
# =============================================================================


class TestAsyncCRUDBaseDelete:
    """测试 AsyncCRUDBase 的删除记录方法"""

    async def test_async_delete_existing_record(
        self, async_session, async_test_user_crud
    ):
        """测试异步删除存在的记录

        验证：可以删除已存在的记录
        """
        # 创建测试用户
        user = await async_test_user_crud.create(
            async_session, {"name": "待删除用户", "email": "delete@test.com"}
        )
        user_id = user.id

        # 删除用户
        deleted_user = await async_test_user_crud.delete(async_session, user_id)

        # 验证返回被删除的用户
        assert deleted_user.id == user_id
        assert deleted_user.name == "待删除用户"

        # 验证用户已被删除
        assert await async_test_user_crud.get(async_session, user_id) is None

    async def test_async_delete_nonexistent_raises_error(
        self, async_session, async_test_user_crud
    ):
        """测试异步删除不存在的记录抛出 NotFoundError

        验证：尝试删除不存在的记录时，应抛出 NotFoundError
        """
        with pytest.raises(NotFoundError) as exc_info:
            await async_test_user_crud.delete(async_session, 99999)

        assert "TestUser" in str(exc_info.value)


# =============================================================================
# TestAsyncCRUDBaseCount - 统计记录数测试
# =============================================================================


class TestAsyncCRUDBaseCount:
    """测试 AsyncCRUDBase 的统计记录数方法"""

    async def test_async_count_all_records(self, async_session, async_test_user_crud):
        """测试异步统计所有记录数

        验证：count 方法应返回所有记录的数量
        """
        # 初始应为 0
        assert await async_test_user_crud.count(async_session) == 0

        # 创建多个用户
        await async_test_user_crud.create(
            async_session, {"name": "用户1", "email": "count1@test.com"}
        )
        await async_test_user_crud.create(
            async_session, {"name": "用户2", "email": "count2@test.com"}
        )
        await async_test_user_crud.create(
            async_session, {"name": "用户3", "email": "count3@test.com"}
        )

        # 验证计数
        assert await async_test_user_crud.count(async_session) == 3

    async def test_async_count_with_filters(self, async_session, async_test_user_crud):
        """测试异步带过滤条件的统计

        验证：count 方法应支持过滤条件
        """
        # 创建不同状态的用户
        await async_test_user_crud.create(
            async_session,
            {"name": "活跃用户", "email": "active@test.com", "is_active": True},
        )
        await async_test_user_crud.create(
            async_session,
            {"name": "非活跃用户1", "email": "inactive1@test.com", "is_active": False},
        )
        await async_test_user_crud.create(
            async_session,
            {"name": "非活跃用户2", "email": "inactive2@test.com", "is_active": False},
        )

        # 统计所有用户
        assert await async_test_user_crud.count(async_session) == 3

        # 统计活跃用户
        assert (
            await async_test_user_crud.count(async_session, filters={"is_active": True})
            == 1
        )

        # 统计非活跃用户
        assert (
            await async_test_user_crud.count(
                async_session, filters={"is_active": False}
            )
            == 2
        )


# =============================================================================
# TestAsyncCRUDBaseExists - 记录存在性检查测试
# =============================================================================


class TestAsyncCRUDBaseExists:
    """测试 AsyncCRUDBase 的记录存在性检查方法"""

    async def test_async_exists_existing_record(
        self, async_session, async_test_user_crud
    ):
        """测试异步存在的记录返回 True

        验证：当记录存在时，exists 方法应返回 True
        """
        # 创建测试用户
        user = await async_test_user_crud.create(
            async_session, {"name": "存在性测试", "email": "exists@test.com"}
        )

        # 验证存在性
        assert await async_test_user_crud.exists(async_session, user.id) is True

    async def test_async_exists_nonexistent_record(
        self, async_session, async_test_user_crud
    ):
        """测试异步不存在的记录返回 False

        验证：当记录不存在时，exists 方法应返回 False
        """
        # 验证不存在的记录
        assert await async_test_user_crud.exists(async_session, 99999) is False
