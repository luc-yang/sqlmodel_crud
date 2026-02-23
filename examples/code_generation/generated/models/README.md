# 代码生成示例

这个目录包含完整的代码生成和使用示例，展示了如何：

1. **定义模型** - 创建 SQLModel 模型类
2. **生成代码** - 使用代码生成器自动生成 CRUD 代码
3. **使用生成的代码** - 测试生成的数据层代码

## 文件说明

| 文件 | 说明 |
|------|------|
| `user_model.py` | 示例模型定义文件，包含 User 模型 |
| `generate_code.py` | 代码生成脚本，运行后会生成 CRUD 代码 |
| `test_generated_crud.py` | 测试脚本，演示如何使用生成的代码 |
| `generated/` | 生成的代码目录（运行 generate_code.py 后创建） |

## 使用步骤

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
# 从项目根目录运行
uv run python examples/code_generation/generate_code.py

# 或者在 examples/code_generation 目录中运行
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
  📄 crud/user.py (crud)
--------------------------------------------------
💡 提示：生成的代码位于 examples/code_generation/generated/ 目录
```

### 步骤 3：测试生成的代码

运行测试脚本验证生成的代码：

```bash
# 从项目根目录运行
uv run python examples/code_generation/test_generated_crud.py

# 或者在 examples/code_generation 目录中运行
uv run python test_generated_crud.py
```

预期输出：

```
🧪 测试生成的 CRUD 代码
--------------------------------------------------
📦 初始化数据库...
✅ 数据库初始化完成

➕ 测试创建用户...
   ✅ 创建用户: ID=1, 姓名=张三

🔍 测试查询用户...
   ✅ 查询到用户: 张三, 邮箱=zhangsan@example.com

✏️ 测试更新用户...
   ✅ 更新后: 姓名=张三丰, 年龄=30

📋 测试查询所有用户...
   ✅ 共有 1 个用户
      - ID=1, 姓名=张三丰

🗑️ 测试删除用户...
   ✅ 已删除用户: 张三丰

🔍 验证删除...
   ✅ 用户已成功删除
--------------------------------------------------
🎉 所有测试通过！
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

## 在 PyQt 应用中使用

生成的代码可以直接在 PyQt 应用中使用：

```python
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
```

## 注意事项

1. **路径不重叠**：确保 `models_path` 和 `output_dir` 不重叠
   - ✅ 正确：`models_path="examples/code_generation"`, `output_dir="examples/code_generation/generated"`
   - ❌ 错误：`models_path="examples/code_generation"`, `output_dir="examples/code_generation"`

2. **重新生成**：如果修改了模型，需要重新运行 `generate_code.py`

3. **数据库位置**：默认数据库文件位于 `AppData/app.db`，可以在 `config.py` 中修改

## 了解更多

- 查看项目根目录的 `README.md` 了解完整文档
- 查看 `examples/basic_usage.py` 了解基础 CRUD 用法
- 查看 `examples/advanced_usage.py` 了解高级功能
