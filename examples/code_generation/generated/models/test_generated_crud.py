"""
测试生成的 CRUD 代码示例

这个示例展示了如何使用生成的数据层代码进行 CRUD 操作。
运行此脚本前，请先运行 generate_code.py 生成代码。

使用方法:
    uv run python test_generated_crud.py
"""

import sys
from pathlib import Path


def main():
    """测试生成的 CRUD 代码"""
    # 添加生成的代码目录到 Python 路径
    current_dir = Path(__file__).parent
    generated_path = current_dir / "generated"

    if not generated_path.exists():
        print("❌ 错误：无法找到生成的代码目录")
        print(f"💡 期望的目录: {generated_path}")
        print("💡 请先运行 generate_code.py 生成代码")
        sys.exit(1)

    # 动态添加路径
    sys.path.insert(0, str(current_dir))
    sys.path.insert(0, str(generated_path))

    try:
        from generated import db, UserCRUD, User
    except ImportError as e:
        print("❌ 错误：无法导入生成的代码")
        print(f"   详细信息: {e}")
        print("💡 请确保已成功运行 generate_code.py")
        sys.exit(1)

    print("🧪 测试生成的 CRUD 代码")
    print("-" * 50)

    # 初始化数据库（自动创建表，应用启动时调用一次）
    print("📦 初始化数据库...")
    db.init_database()
    print("✅ 数据库初始化完成")
    print()

    # 使用 CRUD 操作数据
    user_crud = UserCRUD()

    with db.get_session() as session:
        # 创建用户 - 直接使用字典传入数据
        print("➕ 测试创建用户...")
        user = user_crud.create(
            session, {"name": "张三", "email": "zhangsan@example.com"}
        )
        print(f"   ✅ 创建用户: ID={user.id}, 姓名={user.name}")
        print()

        # 查询用户
        print("🔍 测试查询用户...")
        found = user_crud.get(session, user.id)
        if found:
            print(f"   ✅ 查询到用户: {found.name}, 邮箱={found.email}")
        else:
            print("   ❌ 未找到用户")
        print()

        # 更新用户 - 使用字典进行部分更新
        print("✏️ 测试更新用户...")
        updated = user_crud.update(session, user.id, {"name": "张三丰", "age": 30})
        print(f"   ✅ 更新后: 姓名={updated.name}, 年龄={updated.age}")
        print()

        # 查询所有用户
        print("📋 测试查询所有用户...")
        all_users = user_crud.get_multi(session)
        print(f"   ✅ 共有 {len(all_users)} 个用户")
        for u in all_users:
            print(f"      - ID={u.id}, 姓名={u.name}")
        print()

        # 删除用户
        print("🗑️ 测试删除用户...")
        deleted = user_crud.delete(session, user.id)
        print(f"   ✅ 已删除用户: {deleted.name}")
        print()

        # 验证删除
        print("🔍 验证删除...")
        not_found = user_crud.get(session, user.id)
        if not_found is None:
            print("   ✅ 用户已成功删除")
        else:
            print("   ❌ 用户仍然存在")

    print("-" * 50)
    print("🎉 所有测试通过！")


if __name__ == "__main__":
    main()
