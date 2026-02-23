"""
基础使用示例

展示 SQLModel CRUD 模块的基本用法，包括：
- 定义实体模型
- 配置数据库连接
- 执行 CRUD 操作
"""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, select

# 导入 CRUD 模块
from sqlmodel_crud import CRUDBase, DatabaseManager

# =============================================================================
# 定义实体模型
# =============================================================================


class User(SQLModel, table=True):
    """用户实体模型

    演示一个基本的用户模型，包含常用字段。
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="用户姓名")
    email: str = Field(unique=True, index=True, description="邮箱地址")
    age: Optional[int] = Field(default=None, description="年龄")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class Item(SQLModel, table=True):
    """物品实体模型

    演示与用户关联的物品模型。
    """

    __tablename__ = "items"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="物品名称")
    description: Optional[str] = Field(default=None, description="物品描述")
    price: float = Field(description="价格")
    owner_id: int = Field(foreign_key="users.id", description="所有者ID")


# =============================================================================
# 定义 CRUD 类
# =============================================================================


class UserCRUD(CRUDBase[User, User, User]):
    """用户 CRUD 操作类

    继承 CRUDBase，绑定 User 模型。
    可以在这里添加自定义查询方法。
    """

    def __init__(self):
        super().__init__(User)

    def get_by_email(self, session, email: str) -> Optional[User]:
        """根据邮箱查找用户

        Args:
            session: 数据库会话
            email: 邮箱地址

        Returns:
            用户对象，不存在返回 None
        """
        statement = select(User).where(User.email == email)
        return session.execute(statement).scalars().first()

    def get_active_users(self, session, skip: int = 0, limit: int = 100):
        """获取激活的用户列表

        Args:
            session: 数据库会话
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            用户列表
        """
        return self.get_multi(
            session,
            skip=skip,
            limit=limit,
            filters={"is_active": True},
            order_by=[("created_at", "desc")],
        )


class ItemCRUD(CRUDBase[Item, Item, Item]):
    """物品 CRUD 操作类"""

    def __init__(self):
        super().__init__(Item)

    def get_by_owner(self, session, owner_id: int):
        """获取指定用户的所有物品

        Args:
            session: 数据库会话
            owner_id: 所有者ID

        Returns:
            物品列表
        """
        return self.get_multi(session, filters={"owner_id": owner_id})


# =============================================================================
# 主程序
# =============================================================================


def main():
    """主函数 - 演示 CRUD 操作"""

    # 配置数据库（使用 SQLite 内存数据库便于演示）
    database_url = "sqlite:///example.db"
    db = DatabaseManager(database_url, echo=False)

    # 创建数据库表
    print("=" * 60)
    print("创建数据库表...")
    db.create_tables()
    print("✓ 数据库表创建成功")

    # 初始化 CRUD 实例
    user_crud = UserCRUD()
    item_crud = ItemCRUD()

    # ==========================================================================
    # 1. 创建记录 (Create)
    # ==========================================================================
    print("\n" + "=" * 60)
    print("1. 创建记录 (Create)")
    print("=" * 60)

    with db.get_session() as session:
        # 创建单个用户
        user1 = user_crud.create(
            session, {"name": "张三", "email": "zhangsan@example.com", "age": 25}
        )
        print(f"✓ 创建用户: ID={user1.id}, 姓名={user1.name}, 邮箱={user1.email}")

        # 创建更多用户
        user2 = user_crud.create(
            session,
            {
                "name": "李四",
                "email": "lisi@example.com",
                "age": 30,
                "is_active": False,
            },
        )
        print(f"✓ 创建用户: ID={user2.id}, 姓名={user2.name}, 邮箱={user2.email}")

        user3 = user_crud.create(
            session, {"name": "王五", "email": "wangwu@example.com", "age": 28}
        )
        print(f"✓ 创建用户: ID={user3.id}, 姓名={user3.name}, 邮箱={user3.email}")

    # ==========================================================================
    # 2. 读取记录 (Read)
    # ==========================================================================
    print("\n" + "=" * 60)
    print("2. 读取记录 (Read)")
    print("=" * 60)

    with db.get_session() as session:
        # 根据 ID 获取单条记录
        user = user_crud.get(session, 1)
        print(f"✓ 获取用户 ID=1: {user.name if user else '未找到'}")

        # 获取多条记录（分页）
        users = user_crud.get_multi(session, skip=0, limit=10)
        print(f"✓ 获取用户列表（前10条）: 共 {len(users)} 条记录")
        for u in users:
            print(f"  - ID={u.id}, 姓名={u.name}, 激活={u.is_active}")

        # 使用过滤条件
        active_users = user_crud.get_multi(session, filters={"is_active": True})
        print(f"✓ 激活用户数量: {len(active_users)}")

        # 使用自定义查询方法
        user_by_email = user_crud.get_by_email(session, "lisi@example.com")
        print(f"✓ 根据邮箱查找: {user_by_email.name if user_by_email else '未找到'}")

    # ==========================================================================
    # 3. 更新记录 (Update)
    # ==========================================================================
    print("\n" + "=" * 60)
    print("3. 更新记录 (Update)")
    print("=" * 60)

    with db.get_session() as session:
        # 更新用户信息
        updated_user = user_crud.update(session, 1, {"name": "张三丰", "age": 26})
        print(
            f"✓ 更新用户 ID=1: 姓名改为 {updated_user.name}, 年龄改为 {updated_user.age}"
        )

        # 验证更新结果
        user = user_crud.get(session, 1)
        print(f"✓ 验证更新: 姓名={user.name}, 年龄={user.age}")

    # ==========================================================================
    # 4. 删除记录 (Delete)
    # ==========================================================================
    print("\n" + "=" * 60)
    print("4. 删除记录 (Delete)")
    print("=" * 60)

    with db.get_session() as session:
        # 删除前统计
        count_before = user_crud.count(session)
        print(f"删除前用户总数: {count_before}")

        # 删除用户
        deleted_user = user_crud.delete(session, 3)
        print(f"✓ 删除用户 ID=3: {deleted_user.name}")

        # 删除后统计
        count_after = user_crud.count(session)
        print(f"删除后用户总数: {count_after}")

    # ==========================================================================
    # 5. 批量操作
    # ==========================================================================
    print("\n" + "=" * 60)
    print("5. 批量操作")
    print("=" * 60)

    with db.get_session() as session:
        # 批量创建用户
        new_users = user_crud.create_multi(
            session,
            [
                {"name": "赵六", "email": "zhaoliu@example.com", "age": 35},
                {"name": "钱七", "email": "qianqi@example.com", "age": 40},
                {"name": "孙八", "email": "sunba@example.com", "age": 45},
            ],
        )
        print(f"✓ 批量创建 {len(new_users)} 个用户")
        for u in new_users:
            print(f"  - ID={u.id}, 姓名={u.name}")

    # ==========================================================================
    # 6. 统计和存在性检查
    # ==========================================================================
    print("\n" + "=" * 60)
    print("6. 统计和存在性检查")
    print("=" * 60)

    with db.get_session() as session:
        # 统计所有用户
        total = user_crud.count(session)
        print(f"✓ 用户总数: {total}")

        # 统计激活用户
        active_count = user_crud.count(session, filters={"is_active": True})
        print(f"✓ 激活用户数量: {active_count}")

        # 检查记录是否存在
        exists = user_crud.exists(session, 1)
        print(f"✓ 用户 ID=1 是否存在: {exists}")

        not_exists = user_crud.exists(session, 999)
        print(f"✓ 用户 ID=999 是否存在: {not_exists}")

    # ==========================================================================
    # 7. 异常处理演示
    # ==========================================================================
    print("\n" + "=" * 60)
    print("7. 异常处理演示")
    print("=" * 60)

    from sqlmodel_crud import NotFoundError

    with db.get_session() as session:
        try:
            # 尝试获取不存在的记录
            user = user_crud.get_or_raise(session, 999)
        except NotFoundError as e:
            print(f"✓ 捕获 NotFoundError: {e}")

    # ==========================================================================
    # 清理
    # ==========================================================================
    print("\n" + "=" * 60)
    print("清理数据库...")
    db.drop_tables()
    db.close()
    print("✓ 数据库已清理")

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
