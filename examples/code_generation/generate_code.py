"""
代码生成示例

这个示例展示了如何使用代码生成器根据模型自动生成 CRUD 代码。
运行此脚本前，请确保：
1. 已经定义了模型文件（如 user_model.py）
2. 模型路径和输出目录不重叠
"""

from sqlmodel_crud import generate


def main():
    """生成 CRUD 代码"""
    print("🚀 开始生成代码...")
    print("-" * 50)

    # 测试生成 - 使用正确的路径配置
    # 注意：models_path 应该指向原始模型路径，output_dir 是生成代码的输出目录
    # 两者不应该重叠，否则会导致循环导入问题
    import os

    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 项目根目录
    project_root = os.path.dirname(os.path.dirname(current_dir))

    files = generate(
        models_path=current_dir,  # 原始模型路径（数据源）
        output_dir=os.path.join(current_dir, "generated"),  # 生成代码的输出目录
        use_async=False,
        generators=["crud"],  # 只生成 CRUD，不生成 Schema（PyQt 桌面应用不需要）
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
