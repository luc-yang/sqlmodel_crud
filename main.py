"""
SQLModel CRUD 模块入口文件

提供简单的演示功能，展示 CRUD 模块的基本用法。

用法:
    uv run python main.py
"""

from sqlmodel import SQLModel, Field
from sqlmodel_crud import CRUDBase, DatabaseManager
from typing import Optional


# 定义示例模型
class User(SQLModel, table=True):
    """用户模型示例"""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)


# 创建 CRUD 类
class UserCRUD(CRUDBase[User, User, User]):
    """用户 CRUD 操作类"""

    def __init__(self):
        super().__init__(User)


def main():
    """主函数 - 演示 CRUD 基本操作"""
    print("=" * 50)
    print("SQLModel CRUD 模块演示")
    print("=" * 50)

    # 创建内存数据库（演示用）
    db = DatabaseManager("sqlite:///:memory:")
    db.create_tables()

    with db.get_session() as session:
        user_crud = UserCRUD()

        # 1. 创建用户
        print("\n1. 创建用户:")
        user = user_crud.create(
            session, {"name": "张三", "email": "zhang@example.com"}
        )
        print(f"   创建成功: ID={user.id}, 姓名={user.name}, 邮箱={user.email}")

        # 2. 查询用户
        print("\n2. 查询用户:")
        fetched_user = user_crud.get(session, user.id)
        print(f"   查询结果: {fetched_user}")

        # 3. 更新用户
        print("\n3. 更新用户:")
        updated_user = user_crud.update(session, user.id, {"name": "李四"})
        print(f"   更新成功: 姓名改为 {updated_user.name}")

        # 4. 列出所有用户
        print("\n4. 列出所有用户:")
        users = user_crud.get_multi(session)
        for u in users:
            print(f"   - ID={u.id}, 姓名={u.name}, 邮箱={u.email}")

        # 5. 删除用户
        print("\n5. 删除用户:")
        deleted_user = user_crud.delete(session, user.id)
        print(f"   删除成功: ID={deleted_user.id}")

        # 验证删除
        remaining = user_crud.get_multi(session)
        print(f"   剩余用户数量: {len(remaining)}")

    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)
    print("\n提示: 使用 'sqlmodel-crud --help' 查看代码生成器命令")


if __name__ == "__main__":
    main()
