"""
软删除功能测试模块

测试软删除和恢复功能，包括：
- 软删除操作（设置 is_deleted 和 deleted_at）
- 恢复操作（清除软删除标记）
- 软删除记录的查询过滤
- 软删除对 count 的影响
- 异常处理（不存在的记录、不支持的模型）

支持同步和异步两种模式的测试。
"""

from datetime import datetime, timezone

import pytest

from sqlmodel_crud.exceptions import NotFoundError, ValidationError

# =============================================================================
# TestSoftDelete - 同步软删除测试
# =============================================================================


class TestSoftDelete:
    """测试同步软删除功能"""

    def test_soft_delete_sets_is_deleted_and_deleted_at(
        self, session, soft_delete_user_crud
    ):
        """测试软删除设置标记和时间

        验证：执行软删除后，记录的 is_deleted 应设为 True，deleted_at 应设为当前时间
        """
        # 创建测试用户
        user = soft_delete_user_crud.create(
            session, {"name": "软删除测试用户", "email": "soft_delete@test.com"}
        )

        # 记录创建时间（使用 UTC 时间）
        before_delete = datetime.now(timezone.utc)

        # 执行软删除
        deleted_user = soft_delete_user_crud.delete(session, user.id, soft=True)

        # 验证软删除标记
        assert deleted_user.is_deleted is True
        assert deleted_user.deleted_at is not None
        # 比较时移除时区信息（数据库存储的是 naive datetime）
        assert deleted_user.deleted_at >= before_delete.replace(tzinfo=None)

    def test_soft_delete_record_not_returned_by_get(
        self, session, soft_delete_user_crud
    ):
        """测试软删除后 get 返回 None

        验证：软删除后的记录不应被 get 方法返回
        """
        # 创建测试用户
        user = soft_delete_user_crud.create(
            session, {"name": "软删除查询测试", "email": "soft_get@test.com"}
        )
        user_id = user.id

        # 执行软删除
        soft_delete_user_crud.delete(session, user_id, soft=True)

        # 验证 get 返回 None
        result = soft_delete_user_crud.get(session, user_id)
        assert result is None

    def test_soft_delete_record_not_returned_by_get_multi(
        self, session, soft_delete_user_crud
    ):
        """测试软删除后 get_multi 不返回

        验证：软删除后的记录不应出现在 get_multi 的结果中
        """
        # 创建两个测试用户
        user1 = soft_delete_user_crud.create(
            session, {"name": "用户1", "email": "user1_multi@test.com"}
        )
        user2 = soft_delete_user_crud.create(
            session, {"name": "用户2", "email": "user2_multi@test.com"}
        )

        # 验证初始有2条记录
        results = soft_delete_user_crud.get_multi(session)
        assert len(results) == 2

        # 软删除第一个用户
        soft_delete_user_crud.delete(session, user1.id, soft=True)

        # 验证只剩1条记录
        results = soft_delete_user_crud.get_multi(session)
        assert len(results) == 1
        assert results[0].id == user2.id

    def test_soft_delete_record_included_in_count(self, session, soft_delete_user_crud):
        """测试软删除记录不计入 count

        验证：软删除后的记录不应被 count 方法统计
        """
        # 创建两个测试用户
        user1 = soft_delete_user_crud.create(
            session, {"name": "计数用户1", "email": "count1@test.com"}
        )
        user2 = soft_delete_user_crud.create(
            session, {"name": "计数用户2", "email": "count2@test.com"}
        )

        # 验证初始计数为2
        assert soft_delete_user_crud.count(session) == 2

        # 软删除第一个用户
        soft_delete_user_crud.delete(session, user1.id, soft=True)

        # 验证计数变为1
        assert soft_delete_user_crud.count(session) == 1

    def test_soft_delete_nonexistent_raises_error(self, session, soft_delete_user_crud):
        """测试软删除不存在记录抛出异常

        验证：尝试软删除不存在的记录时，应抛出 NotFoundError
        """
        with pytest.raises(NotFoundError) as exc_info:
            soft_delete_user_crud.delete(session, 99999, soft=True)

        assert "SoftDeleteUser" in str(exc_info.value)
        assert "99999" in str(exc_info.value)

    def test_soft_delete_unsupported_model_raises_error(self, session, test_user_crud):
        """测试不支持软删除的模型抛出 ValidationError

        验证：对没有 is_deleted 和 deleted_at 字段的模型执行软删除时，
        应抛出 ValidationError
        """
        # 创建测试用户（TestUser 不支持软删除）
        user = test_user_crud.create(
            session, {"name": "不支持软删除", "email": "no_soft@test.com"}
        )

        # 尝试软删除应抛出 ValidationError
        with pytest.raises(ValidationError) as exc_info:
            test_user_crud.delete(session, user.id, soft=True)

        assert "不支持软删除" in str(exc_info.value)


# =============================================================================
# TestRestore - 同步恢复测试
# =============================================================================


class TestRestore:
    """测试同步恢复功能"""

    def test_restore_clears_is_deleted_and_deleted_at(
        self, session, soft_delete_user_crud
    ):
        """测试恢复清除标记和时间

        验证：执行恢复后，记录的 is_deleted 应设为 False，deleted_at 应设为 None
        """
        # 创建测试用户
        user = soft_delete_user_crud.create(
            session, {"name": "恢复测试用户", "email": "restore@test.com"}
        )
        user_id = user.id

        # 先软删除
        soft_delete_user_crud.delete(session, user_id, soft=True)

        # 执行恢复
        restored_user = soft_delete_user_crud.restore(session, user_id)

        # 验证恢复后的标记
        assert restored_user.is_deleted is False
        assert restored_user.deleted_at is None

    def test_restore_makes_record_visible_again(self, session, soft_delete_user_crud):
        """测试恢复后记录可再次查询

        验证：恢复后的记录应能被 get 和 get_multi 方法正常查询到
        """
        # 创建测试用户
        user = soft_delete_user_crud.create(
            session, {"name": "可见性测试", "email": "visible@test.com"}
        )
        user_id = user.id

        # 先软删除
        soft_delete_user_crud.delete(session, user_id, soft=True)

        # 验证删除后不可见
        assert soft_delete_user_crud.get(session, user_id) is None
        assert soft_delete_user_crud.count(session) == 0

        # 执行恢复
        soft_delete_user_crud.restore(session, user_id)

        # 验证恢复后可见
        result = soft_delete_user_crud.get(session, user_id)
        assert result is not None
        assert result.id == user_id
        assert result.name == "可见性测试"

        # 验证 get_multi 也能查询到
        results = soft_delete_user_crud.get_multi(session)
        assert len(results) == 1
        assert results[0].id == user_id

        # 验证 count 正确
        assert soft_delete_user_crud.count(session) == 1

    def test_restore_nonexistent_raises_error(self, session, soft_delete_user_crud):
        """测试恢复不存在记录抛出 NotFoundError

        验证：尝试恢复不存在的记录时，应抛出 NotFoundError
        """
        with pytest.raises(NotFoundError) as exc_info:
            soft_delete_user_crud.restore(session, 99999)

        assert "SoftDeleteUser" in str(exc_info.value)
        assert "99999" in str(exc_info.value)

    def test_restore_unsupported_model_raises_error(self, session, test_user_crud):
        """测试不支持软删除的模型抛出 ValidationError

        验证：对没有 is_deleted 和 deleted_at 字段的模型执行恢复时，
        应抛出 ValidationError
        """
        from sqlmodel_crud.base import RestoreMixin

        # 动态创建一个混入 RestoreMixin 的 CRUD 类（模型不支持软删除）
        class UnsupportedCRUD(test_user_crud.__class__, RestoreMixin):
            pass

        # 创建实例
        unsupported_crud = UnsupportedCRUD.__new__(UnsupportedCRUD)
        unsupported_crud.model = test_user_crud.model

        with pytest.raises(ValidationError) as exc_info:
            unsupported_crud.restore(session, 1)

        assert "不支持软删除" in str(exc_info.value)


# =============================================================================
# TestAsyncSoftDelete - 异步软删除测试
# =============================================================================


class TestAsyncSoftDelete:
    """测试异步软删除功能"""

    async def test_async_soft_delete_sets_is_deleted_and_deleted_at(
        self, async_session, async_soft_delete_user_crud
    ):
        """测试异步软删除设置标记

        验证：执行异步软删除后，记录的 is_deleted 应设为 True，deleted_at 应设置时间
        """
        # 创建测试用户
        user = await async_soft_delete_user_crud.create(
            async_session, {"name": "异步软删除用户", "email": "async_soft@test.com"}
        )

        # 记录创建时间（使用 UTC 时间）
        before_delete = datetime.now(timezone.utc)

        # 执行异步软删除
        deleted_user = await async_soft_delete_user_crud.delete(
            async_session, user.id, soft=True
        )

        # 验证软删除标记
        assert deleted_user.is_deleted is True
        assert deleted_user.deleted_at is not None
        # 比较时移除时区信息（数据库存储的是 naive datetime）
        assert deleted_user.deleted_at >= before_delete.replace(tzinfo=None)

    async def test_async_soft_delete_record_not_returned_by_get(
        self, async_session, async_soft_delete_user_crud
    ):
        """测试异步软删除后 get 返回 None

        验证：异步软删除后的记录不应被 get 方法返回
        """
        # 创建测试用户
        user = await async_soft_delete_user_crud.create(
            async_session, {"name": "异步查询测试", "email": "async_get@test.com"}
        )
        user_id = user.id

        # 执行异步软删除
        await async_soft_delete_user_crud.delete(async_session, user_id, soft=True)

        # 验证 get 返回 None
        result = await async_soft_delete_user_crud.get(async_session, user_id)
        assert result is None

    async def test_async_soft_delete_record_not_returned_by_get_multi(
        self, async_session, async_soft_delete_user_crud
    ):
        """测试异步软删除后 get_multi 不返回

        验证：异步软删除后的记录不应出现在 get_multi 的结果中
        """
        # 创建两个测试用户
        user1 = await async_soft_delete_user_crud.create(
            async_session, {"name": "异步用户1", "email": "async_user1@test.com"}
        )
        user2 = await async_soft_delete_user_crud.create(
            async_session, {"name": "异步用户2", "email": "async_user2@test.com"}
        )

        # 验证初始有2条记录
        results = await async_soft_delete_user_crud.get_multi(async_session)
        assert len(results) == 2

        # 异步软删除第一个用户
        await async_soft_delete_user_crud.delete(async_session, user1.id, soft=True)

        # 验证只剩1条记录
        results = await async_soft_delete_user_crud.get_multi(async_session)
        assert len(results) == 1
        assert results[0].id == user2.id


# =============================================================================
# TestAsyncRestore - 异步恢复测试
# =============================================================================


class TestAsyncRestore:
    """测试异步恢复功能"""

    async def test_async_restore_clears_is_deleted_and_deleted_at(
        self, async_session, async_soft_delete_user_crud
    ):
        """测试异步恢复清除标记

        验证：执行异步恢复后，记录的 is_deleted 应设为 False，deleted_at 应设为 None
        """
        # 创建测试用户
        user = await async_soft_delete_user_crud.create(
            async_session, {"name": "异步恢复用户", "email": "async_restore@test.com"}
        )
        user_id = user.id

        # 先异步软删除
        await async_soft_delete_user_crud.delete(async_session, user_id, soft=True)

        # 执行异步恢复
        restored_user = await async_soft_delete_user_crud.restore(
            async_session, user_id
        )

        # 验证恢复后的标记
        assert restored_user.is_deleted is False
        assert restored_user.deleted_at is None

    async def test_async_restore_makes_record_visible_again(
        self, async_session, async_soft_delete_user_crud
    ):
        """测试异步恢复后记录可再次查询

        验证：异步恢复后的记录应能被 get 和 get_multi 方法正常查询到
        """
        # 创建测试用户
        user = await async_soft_delete_user_crud.create(
            async_session, {"name": "异步可见性测试", "email": "async_visible@test.com"}
        )
        user_id = user.id

        # 先异步软删除
        await async_soft_delete_user_crud.delete(async_session, user_id, soft=True)

        # 验证删除后不可见
        assert await async_soft_delete_user_crud.get(async_session, user_id) is None
        assert await async_soft_delete_user_crud.count(async_session) == 0

        # 执行异步恢复
        await async_soft_delete_user_crud.restore(async_session, user_id)

        # 验证恢复后可见
        result = await async_soft_delete_user_crud.get(async_session, user_id)
        assert result is not None
        assert result.id == user_id
        assert result.name == "异步可见性测试"

        # 验证 get_multi 也能查询到
        results = await async_soft_delete_user_crud.get_multi(async_session)
        assert len(results) == 1
        assert results[0].id == user_id

        # 验证 count 正确
        assert await async_soft_delete_user_crud.count(async_session) == 1

    async def test_async_restore_nonexistent_raises_error(
        self, async_session, async_soft_delete_user_crud
    ):
        """测试异步恢复不存在记录抛出异常

        验证：尝试异步恢复不存在的记录时，应抛出 NotFoundError
        """
        with pytest.raises(NotFoundError) as exc_info:
            await async_soft_delete_user_crud.restore(async_session, 99999)

        assert "SoftDeleteUser" in str(exc_info.value)
        assert "99999" in str(exc_info.value)
