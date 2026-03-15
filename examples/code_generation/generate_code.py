"""代码生成示例。"""

from pathlib import Path
from sqlmodel_crud import generate


def main():
    """生成 CRUD 代码。"""
    print("🚀 开始生成代码...")
    print("-" * 50)

    current_dir = Path(__file__).resolve().parent

    files = generate(
        models_path=str(current_dir),
        output_dir=str(current_dir / "generated"),
        use_async=False,
        exclude_models=["BaseModel"],
    )

    print(f"✅ 成功生成了 {len(files)} 个文件:")
    for f in files:
        print(f"  📄 {f.file_path} ({f.generator_type})")

    print("-" * 50)
    print("💡 提示：生成的代码位于 examples/code_generation/generated/ 目录")
    print("💡 你可以运行 test_generated_crud.py 来测试生成的代码")


if __name__ == "__main__":
    main()
