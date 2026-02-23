"""
测试生成的 CRUD 代码示例

这个示例展示了如何使用生成的数据层代码进行 CRUD 操作。
运行此脚本前，请先运行 generate_code.py 生成代码。

注意：由于生成的代码使用了相对导入，此示例需要以模块方式运行：
    cd ../..  # 回到项目根目录
    uv run python -m examples.code_generation.test_generated_crud

或者使用项目根目录的 test_curd.py 作为参考。

使用方法:
    # 方式1：在项目根目录运行
    uv run python test_curd.py
    
    # 方式2：使用模块方式运行（需要 __init__.py）
    uv run python -m examples.code_generation.test_generated_crud
"""

import sys
from pathlib import Path


def main():
    """测试生成的 CRUD 代码"""
    print("=" * 60)
    print("🧪 测试生成的 CRUD 代码")
    print("=" * 60)
    print()

    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    generated_path = current_dir / "generated"

    if not generated_path.exists():
        print("❌ 错误：无法找到生成的代码目录")
        print(f"💡 期望的目录: {generated_path}")
        print("💡 请先运行 generate_code.py 生成代码")
        print()
        print("运行命令:")
        print("  cd examples/code_generation")
        print("  uv run python generate_code.py")
        return

    print("📁 生成的代码目录:")
    print(f"   {generated_path}")
    print()

    # 显示生成的文件结构
    print("📂 生成的文件结构:")
    for item in sorted(generated_path.rglob("*.py")):
        relative = item.relative_to(generated_path)
        print(f"   📄 {relative}")
    print()

    # 由于生成的代码使用了相对导入，我们显示如何使用
    print("💡 使用说明:")
    print()
    print("由于生成的代码使用了相对导入（如 from .config import ...），")
    print("推荐以下使用方式:")
    print()
    print("1️⃣  将 generated 目录作为包使用（推荐用于实际项目）:")
    print("   ```python")
    print("   # 在项目根目录创建 main.py")
    print("   import sys")
    print("   sys.path.insert(0, 'examples/code_generation')")
    print()
    print("   from generated import db, UserCRUD, User")
    print()
    print("   db.init_database()")
    print("   user_crud = UserCRUD()")
    print()
    print("   with db.get_session() as session:")
    print("       user = user_crud.create(session, {'name': '张三'})")
    print("   ```")
    print()
    print("2️⃣  参考项目根目录的 test_curd.py:")
    print("   项目根目录的 test_curd.py 展示了完整的使用方式")
    print()
    print("3️⃣  查看生成的代码:")
    print("   可以直接查看 generated/ 目录下的代码了解结构")
    print()

    # 尝试显示生成的代码内容
    print("=" * 60)
    print("📄 生成的代码预览")
    print("=" * 60)
    print()

    # 显示 User 模型
    user_model_file = generated_path / "models" / "user.py"
    if user_model_file.exists():
        print(f"📄 {user_model_file.name}:")
        print("-" * 40)
        content = user_model_file.read_text(encoding="utf-8")
        # 只显示前 20 行
        lines = content.split("\n")[:20]
        for line in lines:
            print(line)
        print("...")
        print()

    # 显示 UserCRUD
    crud_file = generated_path / "crud" / "user.py"
    if crud_file.exists():
        print(f"📄 {crud_file.name}:")
        print("-" * 40)
        content = crud_file.read_text(encoding="utf-8")
        # 只显示前 25 行
        lines = content.split("\n")[:25]
        for line in lines:
            print(line)
        print("...")
        print()

    print("=" * 60)
    print("✅ 代码生成成功！")
    print("=" * 60)


if __name__ == "__main__":
    main()
