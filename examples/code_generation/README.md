# 代码生成示例

这个目录包含完整的代码生成和使用示例，展示了如何：

1. **定义模型** - 创建 SQLModel 模型类
2. **生成代码** - 使用代码生成器自动生成 CRUD 代码
3. **查看生成的代码** - 了解生成的代码结构和使用方式

## 文件说明

| 文件 | 说明 |
|------|------|
| `user_model.py` | 示例模型定义文件，包含 User 模型 |
| `generate_code.py` | 代码生成脚本，运行后会生成 CRUD 代码 |
| `test_generated_crud.py` | 测试脚本，显示生成的代码结构和使用说明 |
| `generated/` | 生成的代码目录（运行 generate_code.py 后创建） |

## 快速开始

### 步骤 1：查看模型定义

首先查看 `user_model.py` 了解如何定义模型：

```python
class User(SQLModel, table=True):
    """👤 用户模型"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    # ... 其他字段
```

### 步骤 2：生成代码

运行代码生成脚本：

```bash
# 进入示例目录
cd examples/code_generation

# 运行生成脚本
uv run python generate_code.py
```

生成成功后，你会看到类似输出：

```
🚀 开始生成代码...
--------------------------------------------------
✅ 成功生成了 4 个文件:
  📄 config.py (data_layer)
  📄 database.py (data_layer)
  📄 __init__.py (data_layer)
  📄 crud\user.py (crud)
--------------------------------------------------
💡 提示：生成的代码位于 examples/code_generation/generated/ 目录
```

### 步骤 3：查看生成的代码

运行测试脚本查看生成的代码结构：

```bash
uv run python test_generated_crud.py
```

预期输出：

```
============================================================
🧪 测试生成的 CRUD 代码
============================================================

📁 生成的代码目录:
   D:\Code\sqlmodel_curd\examples\code_generation\generated

📂 生成的文件结构:
   📄 __init__.py
   📄 config.py
   📄 crud\user.py
   📄 database.py
   📄 models\user.py

💡 使用说明:
...

============================================================
📄 生成的代码预览
============================================================

📄 user.py:
----------------------------------------
class UserCRUD(CRUDBase[User, User, User]):
    """User 模型的 CRUD 操作类。"""
    ...

============================================================
✅ 代码生成成功！
============================================================
```

## 生成的代码结构

运行生成脚本后，会创建以下目录结构：

```
examples/code_generation/generated/
├── __init__.py          # 统一导出所有接口（db, User, UserCRUD）
├── config.py            # 数据库配置
├── database.py          # 数据库初始化（包含 db 单例）
├── crud/                # CRUD 类目录
│   └── user.py          # UserCRUD 类
└── models/              # 模型目录（从源路径复制）
    └── user.py          # User 模型
```

## 在项目中使用生成的代码

由于生成的代码使用了相对导入（如 `from .config import ...`），推荐以下使用方式：

### 方式 1：将 generated 目录作为包使用（推荐）

```python
import sys
sys.path.insert(0, 'path/to/generated/parent')

from generated import db, UserCRUD, User

# 初始化数据库
db.init_database()

# 使用 CRUD
user_crud = UserCRUD()

with db.get_session() as session:
    # 创建用户
    user = user_crud.create(session, {"name": "张三", "email": "zhangsan@example.com"})
    print(f"✅ 创建用户: ID={user.id}")

    # 查询用户
    found = user_crud.get(session, user.id)
    print(f"🔍 查询用户: {found.name}")

    # 更新用户
    updated = user_crud.update(session, user.id, {"name": "张三丰"})
    print(f"✏️ 更新用户: {updated.name}")

    # 删除用户
    deleted = user_crud.delete(session, user.id)
    print(f"🗑️ 删除用户: {deleted.name}")
```

### 方式 2：参考项目根目录的 test_curd.py

项目根目录的 `test_curd.py` 展示了完整的使用方式。在根目录运行：

```bash
# 在项目根目录运行
uv run python test_curd.py
```

### 方式 3：在 PyQt 应用中使用

```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

# 添加生成的代码路径
sys.path.insert(0, 'path/to/generated/parent')
from generated import db, UserCRUD, User


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化数据库
        db.init_database()
        self.user_crud = UserCRUD()

    def add_user(self, name, email):
        with db.get_session() as session:
            user = self.user_crud.create(session, {
                "name": name,
                "email": email
            })
            return user.id

    def get_all_users(self):
        with db.get_session() as session:
            return self.user_crud.get_multi(session)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

## 完整使用示例

以下是一个完整的使用流程：

```python
# main.py - 项目入口文件
import sys
sys.path.insert(0, 'data')  # 假设生成的代码在 data/ 目录

from generated import db, UserCRUD, User


def main():
    """主函数"""
    # 初始化数据库（应用启动时调用一次）
    print("📦 初始化数据库...")
    db.init_database()
    print("✅ 数据库初始化完成\n")

    # 创建 CRUD 实例
    user_crud = UserCRUD()

    # 使用上下文管理器获取会话
    with db.get_session() as session:
        # 1. 创建用户
        print("➕ 创建用户...")
        user = user_crud.create(session, {
            "name": "张三",
            "email": "zhangsan@example.com",
            "age": 25
        })
        print(f"   ✅ 创建成功: ID={user.id}, 姓名={user.name}\n")

        # 2. 查询用户
        print("🔍 查询用户...")
        found = user_crud.get(session, user.id)
        if found:
            print(f"   ✅ 查询成功: {found.name}, 邮箱={found.email}\n")

        # 3. 更新用户
        print("✏️ 更新用户...")
        updated = user_crud.update(session, user.id, {
            "name": "张三丰",
            "age": 30
        })
        print(f"   ✅ 更新成功: 姓名={updated.name}, 年龄={updated.age}\n")

        # 4. 查询所有用户
        print("📋 查询所有用户...")
        users = user_crud.get_multi(session)
        print(f"   ✅ 共有 {len(users)} 个用户")
        for u in users:
            print(f"      - ID={u.id}, 姓名={u.name}")
        print()

        # 5. 删除用户
        print("🗑️ 删除用户...")
        deleted = user_crud.delete(session, user.id)
        print(f"   ✅ 删除成功: {deleted.name}\n")

        # 6. 验证删除
        print("🔍 验证删除...")
        not_found = user_crud.get(session, user.id)
        if not_found is None:
            print("   ✅ 用户已成功删除\n")

    print("🎉 所有操作完成！")


if __name__ == "__main__":
    main()
```

## 注意事项

1. **路径不重叠**：确保 `models_path` 和 `output_dir` 不重叠
   - ✅ 正确：`models_path="examples/code_generation"`, `output_dir="examples/code_generation/generated"`
   - ❌ 错误：`models_path="examples/code_generation"`, `output_dir="examples/code_generation"`

2. **重新生成**：如果修改了模型，需要重新运行 `generate_code.py`

3. **数据库位置**：默认数据库文件位于 `AppData/app.db`，可以在 `config.py` 中修改

4. **相对导入**：生成的代码使用了相对导入（如 `from .config import ...`），需要作为包使用

## 了解更多

- 查看项目根目录的 `README.md` 了解完整文档
- 查看 `examples/basic_usage.py` 了解基础 CRUD 用法
- 查看 `examples/advanced_usage.py` 了解高级功能
- 查看项目根目录的 `test_curd.py` 了解完整使用示例
