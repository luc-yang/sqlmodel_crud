"""
Mixin 类使用示例

展示如何使用 SoftDeleteMixin、RestoreMixin 和 AsyncRestoreMixin：
- SoftDeleteMixin: 提供软删除功能
- RestoreMixin: 提供同步恢复软删除记录功能
- AsyncRestoreMixin: 提供异步恢复软删除记录功能
"""

import asyncio
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

# 导入 CRUD 模块和 Mixin 类
from sqlmodel_crud import (
    CRUDBase,
    AsyncCRUDBase,
    SoftDeleteMixin,
    RestoreMixin,
    AsyncRestoreMixin,
    DatabaseManager,
    NotFoundError,
    ValidationError,
)

# =============================================================================
# 定义支持软删除的实体模型
# =============================================================================


class Article(SQLModel, table=True):
    """文章实体模型（支持软删除）"""

    __tablename__ = "articles"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="文章标题")
    content: str = Field(description="文章内容")
    author: str = Field(description="作者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    # 软删除字段
    is_deleted: bool = Field(default=False, description="是否已删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")


class Comment(SQLModel, table=True):
    """评论实体模型（支持软删除）"""

    __tablename__ = "comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(description="评论内容")
    article_id: int = Field(foreign_key="articles.id", description="文章ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    # 软删除字段
    is_deleted: bool = Field(default=False, description="是否已删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")


# =============================================================================
# 使用 RestoreMixin 的同步 CRUD 类
# =============================================================================


class ArticleCRUD(CRUDBase[Article, Article, Article], RestoreMixin):
    """文章 CRUD 类（支持软删除恢复）

    继承 CRUDBase 获得基础 CRUD 功能
    继承 RestoreMixin 获得 restore() 方法
    """

    def __init__(self):
        super().__init__(Article)


# =============================================================================
# 使用 AsyncRestoreMixin 的异步 CRUD 类
# =============================================================================


class AsyncCommentCRUD(AsyncCRUDBase[Comment, Comment, Comment], AsyncRestoreMixin):
    """评论异步 CRUD 类（支持软删除恢复）

    继承 AsyncCRUDBase 获得异步 CRUD 功能
    继承 AsyncRestoreMixin 获得异步 restore() 方法
    """

    def __init__(self):
        super().__init__(Comment)


# =============================================================================
# 单独使用 SoftDeleteMixin 的示例
# =============================================================================


class CustomCRUD(SoftDeleteMixin):
    """自定义 CRUD 类（仅使用 SoftDeleteMixin）

    展示如何单独使用 SoftDeleteMixin 来检查软删除支持。
    """

    def __init__(self, model):
        self.model = model

    def check_soft_delete(self) -> bool:
        """检查模型是否支持软删除"""
        return self._has_soft_delete_fields()


# =============================================================================
# 主程序 - 同步示例
# =============================================================================


def sync_demo():
    """同步 CRUD 和 RestoreMixin 演示"""

    print("=" * 60)
    print("同步 CRUD + RestoreMixin 演示")
    print("=" * 60)

    # 配置数据库
    database_url = "sqlite:///mixin_example.db"
    db = DatabaseManager(database_url, echo=False)

    # 创建数据库表
    print("\n创建数据库表...")
    db.create_tables()
    print("✓ 数据库表创建成功")

    # 初始化 CRUD
    article_crud = ArticleCRUD()

    # ==========================================================================
    # 1. 创建文章
    # ==========================================================================
    print("\n" + "-" * 40)
    print("1. 创建文章")
    print("-" * 40)

    with db.get_session() as session:
        article = article_crud.create(
            session,
            {
                "title": "Python 最佳实践",
                "content": "这是一篇关于 Python 编程的文章...",
                "author": "张三",
            },
        )
        print(f"✓ 创建文章: ID={article.id}, 标题={article.title}")
        article_id = article.id

    # ==========================================================================
    # 2. 软删除文章
    # ==========================================================================
    print("\n" + "-" * 40)
    print("2. 软删除文章")
    print("-" * 40)

    with db.get_session() as session:
        # 软删除
        deleted = article_crud.delete(session, article_id, soft=True)
        print(f"✓ 软删除文章: {deleted.title}")
        print(f"  - is_deleted: {deleted.is_deleted}")
        print(f"  - deleted_at: {deleted.deleted_at}")

        # 验证普通查询找不到
        found = article_crud.get(session, article_id)
        print(f"✓ 软删除后普通查询: {'未找到' if found is None else '找到'}")

    # ==========================================================================
    # 3. 恢复软删除的文章（使用 RestoreMixin）
    # ==========================================================================
    print("\n" + "-" * 40)
    print("3. 恢复软删除的文章（RestoreMixin.restore）")
    print("-" * 40)

    with db.get_session() as session:
        # 恢复文章
        restored = article_crud.restore(session, article_id)
        print(f"✓ 恢复文章: {restored.title}")
        print(f"  - is_deleted: {restored.is_deleted}")
        print(f"  - deleted_at: {restored.deleted_at}")

        # 验证恢复后可以查询到
        found = article_crud.get(session, article_id)
        print(f"✓ 恢复后普通查询: {'找到' if found else '未找到'}")

    # ==========================================================================
    # 4. 测试恢复不存在记录的错误处理
    # ==========================================================================
    print("\n" + "-" * 40)
    print("4. 测试错误处理")
    print("-" * 40)

    with db.get_session() as session:
        try:
            article_crud.restore(session, 99999)
        except NotFoundError as e:
            print(f"✓ 恢复不存在的记录时抛出 NotFoundError: {e}")

    # ==========================================================================
    # 5. 单独使用 SoftDeleteMixin
    # ==========================================================================
    print("\n" + "-" * 40)
    print("5. 单独使用 SoftDeleteMixin")
    print("-" * 40)

    custom_crud = CustomCRUD(Article)
    supports_soft_delete = custom_crud.check_soft_delete()
    print(f"✓ Article 模型支持软删除: {supports_soft_delete}")

    # 清理
    print("\n清理数据库...")
    db.drop_tables()
    db.close()
    print("✓ 数据库已清理")


# =============================================================================
# 主程序 - 异步示例
# =============================================================================


async def async_demo():
    """异步 CRUD 和 AsyncRestoreMixin 演示"""

    print("\n" + "=" * 60)
    print("异步 CRUD + AsyncRestoreMixin 演示")
    print("=" * 60)

    # 配置异步数据库
    database_url = "sqlite+aiosqlite:///async_mixin_example.db"
    db = DatabaseManager(database_url, echo=False)

    # 异步创建数据库表
    print("\n异步创建数据库表...")
    await db.create_tables_async()
    print("✓ 数据库表创建成功")

    # 初始化异步 CRUD
    comment_crud = AsyncCommentCRUD()

    # ==========================================================================
    # 1. 异步创建评论
    # ==========================================================================
    print("\n" + "-" * 40)
    print("1. 异步创建评论")
    print("-" * 40)

    async with db.get_async_session() as session:
        comment = await comment_crud.create(
            session,
            {
                "content": "这是一篇很好的文章！",
                "article_id": 1,
            },
        )
        print(f"✓ 创建评论: ID={comment.id}")
        comment_id = comment.id

    # ==========================================================================
    # 2. 异步软删除评论
    # ==========================================================================
    print("\n" + "-" * 40)
    print("2. 异步软删除评论")
    print("-" * 40)

    async with db.get_async_session() as session:
        # 软删除
        deleted = await comment_crud.delete(session, comment_id, soft=True)
        print(f"✓ 软删除评论: ID={deleted.id}")
        print(f"  - is_deleted: {deleted.is_deleted}")

        # 验证普通查询找不到
        found = await comment_crud.get(session, comment_id)
        print(f"✓ 软删除后普通查询: {'未找到' if found is None else '找到'}")

    # ==========================================================================
    # 3. 异步恢复软删除的评论（使用 AsyncRestoreMixin）
    # ==========================================================================
    print("\n" + "-" * 40)
    print("3. 异步恢复软删除的评论（AsyncRestoreMixin.restore）")
    print("-" * 40)

    async with db.get_async_session() as session:
        # 恢复评论
        restored = await comment_crud.restore(session, comment_id)
        print(f"✓ 恢复评论: ID={restored.id}")
        print(f"  - is_deleted: {restored.is_deleted}")
        print(f"  - deleted_at: {restored.deleted_at}")

        # 验证恢复后可以查询到
        found = await comment_crud.get(session, comment_id)
        print(f"✓ 恢复后普通查询: {'找到' if found else '未找到'}")

    # ==========================================================================
    # 4. 测试异步恢复不存在记录的错误处理
    # ==========================================================================
    print("\n" + "-" * 40)
    print("4. 测试异步错误处理")
    print("-" * 40)

    async with db.get_async_session() as session:
        try:
            await comment_crud.restore(session, 99999)
        except NotFoundError as e:
            print(f"✓ 异步恢复不存在的记录时抛出 NotFoundError: {e}")

    # 清理
    print("\n清理数据库...")
    await db.drop_tables_async()
    await db.close_async()
    print("✓ 数据库已清理")


# =============================================================================
# 运行示例
# =============================================================================


def main():
    """主函数"""

    # 运行同步示例
    sync_demo()

    # 运行异步示例
    asyncio.run(async_demo())

    print("\n" + "=" * 60)
    print("Mixin 使用示例运行完成！")
    print("=" * 60)
    print("\n总结:")
    print("  - SoftDeleteMixin: 提供 _has_soft_delete_fields() 和")
    print("    _apply_soft_delete_filter() 方法")
    print("  - RestoreMixin: 为同步 CRUD 提供 restore() 方法")
    print("  - AsyncRestoreMixin: 为异步 CRUD 提供 restore() 方法")
    print("=" * 60)


if __name__ == "__main__":
    main()
