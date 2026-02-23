"""
异步使用示例

展示如何使用 AsyncCRUDBase 进行异步 CRUD 操作，包括：
- 异步数据库连接配置
- 继承 AsyncCRUDBase 创建 CRUD 类
- 所有异步 CRUD 操作演示
- 分页、过滤、排序功能
- 批量创建与分批插入
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

# 导入 CRUD 模块
from sqlmodel_crud import DatabaseManager, AsyncCRUDBase, NotFoundError

# =============================================================================
# 定义实体模型
# =============================================================================


class Product(SQLModel, table=True):
    """产品实体模型"""

    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    price: float = Field(description="价格")
    stock: int = Field(default=0, description="库存")
    is_available: bool = Field(default=True, description="是否可售")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


# =============================================================================
# 继承 AsyncCRUDBase 创建 CRUD 类
# =============================================================================


class ProductCRUD(AsyncCRUDBase[Product, Product, Product]):
    """产品 CRUD 类

    继承 AsyncCRUDBase，自动获得所有异步 CRUD 操作能力。
    """

    def __init__(self):
        """初始化 ProductCRUD 实例"""
        super().__init__(Product)


# =============================================================================
# 异步主程序
# =============================================================================


async def main():
    """异步主函数"""

    # 配置异步数据库（使用 aiosqlite）
    database_url = "sqlite+aiosqlite:///async_example.db"
    db = DatabaseManager(database_url, echo=False)

    # 异步创建数据库表
    print("=" * 60)
    print("异步创建数据库表...")
    await db.create_tables_async()
    print("✓ 数据库表创建成功")

    # 初始化 CRUD 实例
    product_crud = ProductCRUD()

    # ==========================================================================
    # 1. 创建记录
    # ==========================================================================
    print("\n" + "=" * 60)
    print("1. 创建记录")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 创建单条记录 - 使用字典
        product1 = await product_crud.create(
            session,
            {
                "name": "笔记本电脑",
                "description": "高性能商务笔记本",
                "price": 5999.00,
                "stock": 100,
            },
        )
        print(f"✓ 创建产品: ID={product1.id}, 名称={product1.name}")

        # 创建单条记录 - 使用模型实例
        product2_data = Product(
            name="无线鼠标",
            description="人体工学设计",
            price=99.00,
            stock=500,
        )
        product2 = await product_crud.create(session, product2_data)
        print(f"✓ 创建产品: ID={product2.id}, 名称={product2.name}")

        # 创建更多记录用于后续演示
        product3 = await product_crud.create(
            session,
            {
                "name": "机械键盘",
                "description": "RGB背光机械键盘",
                "price": 299.00,
                "stock": 200,
                "is_available": False,
            },
        )
        print(f"✓ 创建产品: ID={product3.id}, 名称={product3.name}")

    # ==========================================================================
    # 2. 读取记录 - 单条查询
    # ==========================================================================
    print("\n" + "=" * 60)
    print("2. 读取记录 - 单条查询")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 根据 ID 获取单条记录
        product = await product_crud.get(session, 1)
        if product:
            print(f"✓ 获取产品 ID=1: {product.name} (价格: {product.price})")

        # 获取不存在的记录
        not_found = await product_crud.get(session, 999)
        print(f"✓ 获取产品 ID=999: {'未找到' if not_found is None else '找到'}")

        # 使用 get_or_raise（记录不存在时会抛出异常）
        try:
            product = await product_crud.get_or_raise(session, 2)
            print(f"✓ get_or_raise ID=2: {product.name}")
        except NotFoundError as e:
            print(f"✗ 记录不存在: {e}")

        # 检查记录是否存在
        exists = await product_crud.exists(session, 1)
        print(f"✓ 产品 ID=1 是否存在: {exists}")

        not_exists = await product_crud.exists(session, 999)
        print(f"✓ 产品 ID=999 是否存在: {not_exists}")

    # ==========================================================================
    # 3. 读取记录 - 多条查询、分页、过滤
    # ==========================================================================
    print("\n" + "=" * 60)
    print("3. 读取记录 - 多条查询、分页、过滤")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 获取所有记录
        all_products = await product_crud.get_multi(session, skip=0, limit=100)
        print(f"✓ 所有产品数量: {len(all_products)}")

        # 分页查询
        page1 = await product_crud.get_multi(session, skip=0, limit=2)
        print(f"✓ 第1页 (limit=2): {len(page1)} 条记录")
        for p in page1:
            print(f"  - ID={p.id}, {p.name}")

        page2 = await product_crud.get_multi(session, skip=2, limit=2)
        print(f"✓ 第2页 (skip=2, limit=2): {len(page2)} 条记录")
        for p in page2:
            print(f"  - ID={p.id}, {p.name}")

        # 按条件过滤
        available_products = await product_crud.get_multi(
            session, filters={"is_available": True}
        )
        print(f"✓ 可售产品数量: {len(available_products)}")

        # 排序查询
        sorted_products = await product_crud.get_multi(
            session, order_by=[("price", "desc")]
        )
        print("✓ 按价格倒序排列:")
        for p in sorted_products:
            print(f"  - ID={p.id}, {p.name}, 价格={p.price}")

    # ==========================================================================
    # 4. 更新记录
    # ==========================================================================
    print("\n" + "=" * 60)
    print("4. 更新记录")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 更新单条记录 - 使用字典
        updated = await product_crud.update(
            session, 1, {"price": 5499.00, "stock": 150}
        )
        print(f"✓ 更新产品 ID=1:")
        print(f"  - 价格: {updated.price}")
        print(f"  - 库存: {updated.stock}")

    # ==========================================================================
    # 5. 删除记录
    # ==========================================================================
    print("\n" + "=" * 60)
    print("5. 删除记录")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 统计删除前数量
        count_before = await product_crud.count(session)
        print(f"删除前产品总数: {count_before}")

        # 删除产品
        deleted = await product_crud.delete(session, 3)
        print(f"✓ 删除产品 ID=3: {deleted.name}")

        # 统计删除后数量
        count_after = await product_crud.count(session)
        print(f"删除后产品总数: {count_after}")

    # ==========================================================================
    # 6. 批量创建与分批插入
    # ==========================================================================
    print("\n" + "=" * 60)
    print("6. 批量创建与分批插入")
    print("=" * 60)

    # 准备批量创建的数据
    bulk_data = [
        {
            "name": f"批量产品 {i:03d}",
            "description": f"这是第 {i} 个批量创建的产品",
            "price": float(i * 10),
            "stock": i * 10,
        }
        for i in range(1, 26)  # 创建 25 条记录
    ]

    print(f"准备批量创建 {len(bulk_data)} 条记录...")

    async with db.get_async_session() as session:
        # 使用分批插入，每批 10 条
        created = await product_crud.create_multi(session, bulk_data, batch_size=10)
        print(f"✓ 成功创建 {len(created)} 条记录")
        print(f"  - 使用 batch_size=10，共分 {(len(bulk_data) - 1) // 10 + 1} 批插入")

        # 验证创建结果
        total_count = await product_crud.count(session)
        print(f"✓ 当前产品总数: {total_count}")

    # 重新查询显示批量创建的记录
    async with db.get_async_session() as session:
        bulk_products = await product_crud.get_multi(
            session, filters={"name": "批量产品 001"}
        )
        print("✓ 查询批量创建的记录:")
        for product in bulk_products:
            print(f"  - ID={product.id}, {product.name}, 价格={product.price}")

    # ==========================================================================
    # 7. 统计与存在性检查
    # ==========================================================================
    print("\n" + "=" * 60)
    print("7. 统计与存在性检查")
    print("=" * 60)

    async with db.get_async_session() as session:
        # 统计所有记录
        total = await product_crud.count(session)
        print(f"✓ 产品总数: {total}")

        # 按条件统计
        available_count = await product_crud.count(
            session, filters={"is_available": True}
        )
        print(f"✓ 可售产品数量: {available_count}")

        # 存在性检查
        print("\n存在性检查:")
        for id in [1, 2, 3, 100]:
            exists = await product_crud.exists(session, id)
            status = "存在" if exists else "不存在"
            print(f"  - 产品 ID={id}: {status}")

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
    print("  ✓ 记录删除")
    print("  ✓ 批量创建（支持分批插入）")
    print("  ✓ 统计功能（总数、条件统计）")
    print("  ✓ 存在性检查")


if __name__ == "__main__":
    asyncio.run(main())
