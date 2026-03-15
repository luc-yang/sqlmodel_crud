# SQLModel CRUD API

## 概览

`sqlmodel_crud` 提供 5 组核心能力：

1. `CRUDBase` / `AsyncCRUDBase`：可复用同步/异步 CRUD 基类  
2. `DatabaseManager`：统一的会话与事务边界  
3. `ModelScanner`：扫描 SQLModel 模型元数据  
4. `CodeGenerator`：基于模型生成 CRUD 与数据层文件  
5. `ChangeDetector`：模型快照与变更检测

当前生成契约为 **CRUD-only**。

## 事务语义

- CRUD 写操作（`create/create_multi/update/delete/restore`）只执行 `add/flush/refresh`。
- `commit/rollback` 由 `DatabaseManager.get_session()` / `get_async_session()` 上下文统一处理。
- 这保证了一个 session 上下文中的多步写操作具备原子性。

## 扫描器接口

- 统一入口：`ModelScanner.scan(target)`
- 支持输入：
  - 目录路径
  - 单文件路径（`.py`）
  - Python 模块路径（如 `app.models`）
- 不可解析时统一抛出 `ValueError`。

## 配置加载顺序

`load_config()` 的优先级（高到低）：

1. 环境变量 `SQLMODEL_CRUD_*`
2. 显式配置文件 `--config`
3. `pyproject.toml` 的 `[tool.sqlmodel-crud]`
4. `.sqlmodel-crud.toml`
5. 内置默认值

说明：

- `GeneratorConfig` 构造阶段只做结构校验，不做路径存在性副作用校验。
- 运行前请调用 `config.validate_all()` 做路径/目录的运行时校验。

## CLI

```bash
sqlmodel-crud init --models-path app/models --output-dir app/generated
sqlmodel-crud generate --force
sqlmodel-crud generate --models-path app/models --dry-run
sqlmodel-crud version
```

- `generate` 的行为是：加载配置 -> 应用 CLI 覆盖 -> `validate_all()` -> 扫描 -> 生成 ->（非 dry-run）写盘与快照。
- 非 UTF 终端会自动将状态符号降级为 ASCII 前缀（如 `[OK]`、`[WARN]`）。

## 关键类型

- `GeneratorConfig`
- `ModelMeta` / `FieldMeta`
- `GeneratedFile`
- `ModelChange`

## 生成文件契约

当 `generate_data_layer=True` 时，生成器会输出一套完整的数据层：

- `config.py`
  - `DatabaseConfig`
  - `default_config`
- `database.py`
  - `DatabaseInitializer`
  - `DatabaseManager`
  - 模块级 `db`
  - `init_database(...)`
  - `get_session()` 或 `get_async_session()`
- `__init__.py`
  - 统一导出配置、数据库入口、模型和 CRUD 类
- `crud/<model>.py`
  - 每个模型一个 CRUD 类
- `models/`
  - 复制后的模型文件（当 `generate_model_copy=True` 时）

如果 `generate_data_layer=False`，则只生成 `crud/` 相关文件。

## 生成代码的同步用法

推荐在项目入口初始化一次数据库配置，在业务模块中短生命周期获取 session：

```python
# app/db.py
from app.generated import DatabaseConfig, init_database


def bootstrap_database() -> None:
    init_database(DatabaseConfig(db_name="app.db", db_dir="data"))
```

```python
# app/services/user_service.py
from app.generated import UserCRUD, get_session

user_crud = UserCRUD()


def get_user(user_id: int):
    with get_session() as session:
        return user_crud.get(session, user_id)


def create_user(data: dict):
    with get_session() as session:
        return user_crud.create(session, data)
```

## 生成代码的异步用法

当 `use_async=True` 时，生成层会导出异步入口：

```python
# app/db.py
from app.generated import DatabaseConfig, init_database


async def bootstrap_database() -> None:
    await init_database(DatabaseConfig(db_name="app.db", db_dir="data"))
```

```python
# app/services/user_service.py
from app.generated import UserCRUD, get_async_session

user_crud = UserCRUD()


async def create_user(data: dict):
    async with get_async_session() as session:
        return await user_crud.create(session, data)
```

## 事务组合方式

当多个写操作必须共用一个事务时，由最外层统一打开 session，再把 session 往下传：

```python
from app.generated import UserCRUD, ProfileCRUD, get_session

user_crud = UserCRUD()
profile_crud = ProfileCRUD()


def register_user(user_data: dict, profile_data: dict):
    with get_session() as session:
        user = user_crud.create(session, user_data)
        profile = profile_crud.create(
            session, {**profile_data, "user_id": user.id}
        )
        return user, profile
```

不要在每个仓储方法内部各自重新开 session，否则事务会被切碎。

## 快速示例

```python
from sqlmodel_crud import ModelScanner, CodeGenerator, GeneratorConfig

config = GeneratorConfig(
    models_path="app/models",
    output_dir="app/generated",
)
config.validate_all()

scanner = ModelScanner(config)
models = scanner.scan(config.models_path)

generator = CodeGenerator(config)
files = generator.generate(models)
generator.write_files(files, dry_run=False)
```
