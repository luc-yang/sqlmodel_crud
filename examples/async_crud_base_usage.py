"""
AsyncCRUDBase 使用示例

展示如何使用 AsyncCRUDBase 基类进行异步 CRUD 操作，包括：
- 支持软删除的模型定义
- 继承 AsyncCRUDBase 创建 CRUD 类
- 所有异步 CRUD 操作演示
- 软删除与硬删除的区别
- 批量创建与分批插入
"""

import asyncio
from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, select
from sqlalchemy import func

# 导入 CRUD 模块
from sqlmodel_crud import DatabaseManager, AsyncCRUDBase, NotFoundError

# =============================================================================
# 定义支持软删除的实体模型
# =============================================================================


class Article(SQLModel, table=True):
    """文章实体模型

    支持软删除功能，包含 is_deleted 和 deleted_at 字段。
    软删除的记录在普通查询中会被自动过滤掉。
    """

    __tablename__ = "articles"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="文章标题")
    content: str = Field(description="文章内容")
    author: str = Field(description="作者")
    category: Optional[str] = Field(default=None, description="分类")
    views: int = Field(default=0, description="浏览次数")

    # 软删除字段
    is_deleted: bool = Field(default=False, description="是否已软删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")

    # 时间戳字段
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


# =============================================================================
# 继承 AsyncCRUDBase 创建 CRUD 类
# =============================================================================


class ArticleCRUD(AsyncCRUDBase[Article, Article, Article]):
    """文章 CRUD 类

    继承 AsyncCRUDBase，自动获得所有异步 CRUD 操作能力。
    由于 Article 模型包含 is_deleted 和 deleted_at 字段，
    自动支持软删除功能。
    """

    def __init__(self):
        """初始化 ArticleCRUD 实例"""
        super().__init__(Article)

    async def get_by_author(
        self, session, author: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """根据作者获取文章列表

        自定义查询方法，展示如何扩展基础 CRUD 功能。

        Args:
            session: 异步数据库会话
            author: 作者名称
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            文章列表
        """
        statement = select(Article).where(Article.author == author)
        statement = self._apply_soft_delete_filter(statement)
        statement = statement.offset(skip).limit(limit)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def increment_views(self, session, id: int) -> Optional[Article]:
        """增加文章浏览次数

        自定义更新方法，展示如何扩展基础 CRUD 功能。

        Args:
            session: 异步数据库会话
            id: 文章 ID

        Returns:
            更新后的文章对象，不存在时返回 None
        """
        article = await self.get(session, id)
        if article:
            article.views += 1
            article.updated_at = datetime.now()
            await session.commit()
            await session.refresh(article)
        return article


# =============================================================================
# 异步主程序
# =============================================================================


async def main():
    """异步主函数"""

    # 配置异步数据库（使用 aiosqlite）
    database_url = "sqlite+aiosqlite:///async_crud_base_example.db"
    db = DatabaseManager(database_url, echo=False)

    # 异步创建数据库表
    print("=" * 60)
    print("异步创建数据库表...")
    await db.create_tables_async()
    print("✓ 数据库表创建成功")

    # 初始化 CRUD 实例
    article_crud = ArticleCRUD()

    # ==========================================================================
    # 1. 创建记录
    # ==========================================================================
    print("\n" + "=" * 60)
    print("1. 创建记录")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 创建单条记录 - 使用字典
        article1 = await article_crud.create(
            session,
            {
                "title": "Python 异步编程指南",
                "content": "本文介绍 Python 中 asyncio 的使用方法...",
                "author": "张三",
                "category": "技术",
            },
        )
        print(f"✓ 创建文章: ID={article1.id}, 标题={article1.title}")

        # 创建单条记录 - 使用模型实例
        article2_data = Article(
            title="SQLModel 快速入门",
            content="SQLModel 是一个结合了 SQLAlchemy 和 Pydantic 的 ORM...",
            author="李四",
            category="技术",
        )
        article2 = await article_crud.create(session, article2_data)
        print(f"✓ 创建文章: ID={article2.id}, 标题={article2.title}")

        # 创建更多记录用于后续演示
        article3 = await article_crud.create(
            session,
            {
                "title": "生活随笔",
                "content": "记录生活中的点滴...",
                "author": "王五",
                "category": "生活",
            },
        )
        print(f"✓ 创建文章: ID={article3.id}, 标题={article3.title}")

    # ==========================================================================
    # 2. 读取记录 - 单条查询
    # ==========================================================================
    print("\n" + "=" * 60)
    print("2. 读取记录 - 单条查询")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 根据 ID 获取单条记录
        article = await article_crud.get(session, 1)
        if article:
            print(f"✓ 获取文章 ID=1: {article.title} (作者: {article.author})")

        # 获取不存在的记录
        not_found = await article_crud.get(session, 999)
        print(f"✓ 获取文章 ID=999: {'未找到' if not_found is None else '找到'}")

        # 使用 get_or_raise（记录不存在时会抛出异常）
        try:
            article = await article_crud.get_or_raise(session, 2)
            print(f"✓ get_or_raise ID=2: {article.title}")
        except NotFoundError as e:
            print(f"✗ 记录不存在: {e}")

        # 检查记录是否存在
        exists = await article_crud.exists(session, 1)
        print(f"✓ 文章 ID=1 是否存在: {exists}")

        not_exists = await article_crud.exists(session, 999)
        print(f"✓ 文章 ID=999 是否存在: {not_exists}")

    # ==========================================================================
    # 3. 读取记录 - 多条查询、分页、过滤
    # ==========================================================================
    print("\n" + "=" * 60)
    print("3. 读取记录 - 多条查询、分页、过滤")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 获取所有记录
        all_articles = await article_crud.get_multi(session, skip=0, limit=100)
        print(f"✓ 所有文章数量: {len(all_articles)}")

        # 分页查询
        page1 = await article_crud.get_multi(session, skip=0, limit=2)
        print(f"✓ 第1页 (limit=2): {len(page1)} 条记录")
        for a in page1:
            print(f"  - ID={a.id}, {a.title}")

        page2 = await article_crud.get_multi(session, skip=2, limit=2)
        print(f"✓ 第2页 (skip=2, limit=2): {len(page2)} 条记录")
        for a in page2:
            print(f"  - ID={a.id}, {a.title}")

        # 按条件过滤
        tech_articles = await article_crud.get_multi(
            session, filters={"category": "技术"}
        )
        print(f"✓ 技术类文章数量: {len(tech_articles)}")

        # 按作者过滤（使用自定义方法）
        zhang_articles = await article_crud.get_by_author(session, "张三")
        print(f"✓ 张三的文章数量: {len(zhang_articles)}")

        # 排序查询
        sorted_articles = await article_crud.get_multi(
            session, order_by=[("created_at", "desc")]
        )
        print("✓ 按创建时间倒序排列:")
        for a in sorted_articles:
            print(f"  - ID={a.id}, {a.title}")

    # ==========================================================================
    # 4. 更新记录
    # ==========================================================================
    print("\n" + "=" * 60)
    print("4. 更新记录")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 更新单条记录 - 使用字典
        updated = await article_crud.update(
            session, 1, {"title": "Python 异步编程完全指南", "category": "编程"}
        )
        print(f"✓ 更新文章 ID=1:")
        print(f"  - 标题: {updated.title}")
        print(f"  - 分类: {updated.category}")

        # 使用自定义方法增加浏览次数
        for _ in range(5):
            await article_crud.increment_views(session, 1)
        article = await article_crud.get(session, 1)
        print(f"✓ 文章 ID=1 浏览次数: {article.views}")

    # ==========================================================================
    # 5. 软删除与硬删除对比
    # ==========================================================================
    print("\n" + "=" * 60)
    print("5. 软删除与硬删除对比")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 删除前统计
        count_before = await article_crud.count(session)
        print(f"删除前文章总数: {count_before}")

        # 软删除文章 ID=3
        print("\n执行软删除 (ID=3)...")
        soft_deleted = await article_crud.delete(session, 3, soft=True)
        print(f"✓ 已软删除文章: {soft_deleted.title}")
        print(f"  - is_deleted: {soft_deleted.is_deleted}")
        print(f"  - deleted_at: {soft_deleted.deleted_at}")

        # 软删除后统计（普通查询不会返回软删除记录）
        count_after_soft = await article_crud.count(session)
        print(f"\n软删除后文章总数（普通查询）: {count_after_soft}")

        # 尝试获取软删除的记录
        deleted_article = await article_crud.get(session, 3)
        print(
            f"✓ 尝试获取软删除文章 ID=3: {'未找到' if deleted_article is None else '找到'}"
        )

        # 直接查询数据库验证软删除记录仍然存在
        statement = select(Article).where(Article.id == 3)
        result = await session.execute(statement)
        raw_article = result.scalar_one_or_none()
        if raw_article:
            print(f"✓ 数据库中仍存在该记录（is_deleted={raw_article.is_deleted}）")

        # 硬删除文章 ID=2
        print("\n执行硬删除 (ID=2)...")
        hard_deleted = await article_crud.delete(session, 2, soft=False)
        print(f"✓ 已硬删除文章: {hard_deleted.title}")

        # 硬删除后统计
        count_after_hard = await article_crud.count(session)
        print(f"\n硬删除后文章总数: {count_after_hard}")

        # 验证硬删除的记录不存在
        hard_deleted_check = await article_crud.get(session, 2)
        print(
            f"✓ 尝试获取硬删除文章 ID=2: {'未找到' if hard_deleted_check is None else '找到'}"
        )

    # ==========================================================================
    # 6. 批量创建与分批插入
    # ==========================================================================
    print("\n" + "=" * 60)
    print("6. 批量创建与分批插入")
    print("=" * 60)

    # 准备批量创建的数据
    bulk_data = [
        {
            "title": f"批量文章 {i:03d}",
            "content": f"这是第 {i} 篇批量创建的文章内容...",
            "author": "批量作者",
            "category": "批量测试",
        }
        for i in range(1, 26)  # 创建 25 条记录
    ]

    print(f"准备批量创建 {len(bulk_data)} 条记录...")

    async with db.get_async_session() as session:
        # 使用分批插入，每批 10 条
        created_count = len(bulk_data)
        _ = await article_crud.create_multi(session, bulk_data, batch_size=10)
        print(f"✓ 成功创建 {created_count} 条记录")
        print(f"  - 使用 batch_size=10，共分 {(len(bulk_data) - 1) // 10 + 1} 批插入")

        # 验证创建结果
        total_count = await article_crud.count(session)
        print(f"✓ 当前文章总数: {total_count}")

    # 重新查询显示批量创建的记录
    async with db.get_async_session() as session:
        bulk_articles = await article_crud.get_multi(
            session, filters={"author": "批量作者"}, limit=5
        )
        print("✓ 前 5 条批量创建的记录:")
        for article in bulk_articles:
            print(f"  - ID={article.id}, {article.title}")

    # ==========================================================================
    # 7. 统计与存在性检查
    # ==========================================================================
    print("\n" + "=" * 60)
    print("7. 统计与存在性检查")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 统计所有记录
        total = await article_crud.count(session)
        print(f"✓ 文章总数: {total}")

        # 按条件统计
        tech_count = await article_crud.count(session, filters={"category": "编程"})
        print(f"✓ 编程类文章数量: {tech_count}")

        bulk_count = await article_crud.count(session, filters={"author": "批量作者"})
        print(f"✓ 批量作者的文章数量: {bulk_count}")

        # 存在性检查
        print("\n存在性检查:")
        for id in [1, 2, 3, 100]:
            exists = await article_crud.exists(session, id)
            status = "存在" if exists else "不存在"
            print(f"  - 文章 ID={id}: {status}")

    # ==========================================================================
    # 清理
    # ==========================================================================
    print("\n" + "=" * 60)
    print("清理数据库...")
    await db.drop_tables_async()
    await db.close_async()
    print("✓ 数据库已清理")

    print("\n" + "=" * 60)
    print("AsyncCRUDBase 示例运行完成！")
    print("=" * 60)
    print("\n功能演示总结:")
    print("  ✓ 单条记录创建（字典和模型实例）")
    print("  ✓ 单条记录查询（get, get_or_raise）")
    print("  ✓ 多条记录查询（分页、过滤、排序）")
    print("  ✓ 记录更新")
    print("  ✓ 软删除（记录标记为删除但保留数据）")
    print("  ✓ 硬删除（永久删除记录）")
    print("  ✓ 批量创建（支持分批插入）")
    print("  ✓ 统计功能（总数、条件统计）")
    print("  ✓ 存在性检查")
    print("  ✓ 自定义 CRUD 方法扩展")


if __name__ == "__main__":
    asyncio.run(main())
