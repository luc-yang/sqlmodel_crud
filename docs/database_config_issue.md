# SQLModel CRUD 数据库配置问题分析与解决方案

## 问题描述

在使用 sqlmodel_crud 生成的数据库代码时，如果用户在 `main.py` 中自定义数据库配置（如数据库名称、路径），可能会出现**同时产生两个数据库文件**的问题。

### 示例场景

```python
# main.py
from app.view.main_window import MainWindow  # 导入时触发 DatabaseManager 单例创建
from app.data.database import init_database, DatabaseConfig

# 创建自定义配置
db_config = DatabaseConfig(db_name="fpdcm.db")
init_database(db_config)  # 期望使用 fpdcm.db
```

**结果**：同时产生 `app.db` 和 `fpdcm.db` 两个文件。

## 问题原因

### 根本原因

`DatabaseManager` 单例在**首次实例化时**确定配置，且不可更改。

### 时序分析

```
1. main.py: from app.view.main_window import MainWindow
   ↓
2. MainWindow 导入链触发 Presenter 导入
   ↓
3. Presenter.__init__ 中调用 DatabaseManager()
   ↓
4. DatabaseManager 单例首次创建，使用 default_config（app.db）
   ↓
5. main.py: init_database(db_config) 使用自定义配置（fpdcm.db）
   ↓
6. 结果：两个数据库文件都被创建
```

### 代码层面的问题

```python
# database.py

# 模块导入时立即创建实例
db = DatabaseManager()  # 使用 default_config

class DatabaseManager:
    _instance = None
    
    def __init__(self, db_config=None):
        if self._initialized:
            return  # 单例已存在，直接返回，不接受新配置
        
        self.db_config = db_config or default_config  # 首次确定配置
        self._engine = create_engine(...)  # 立即创建引擎，连接数据库
        self._initialized = True
```

问题：
1. 模块级实例 `db = DatabaseManager()` 在导入时立即创建
2. 引擎立即创建，立即连接数据库，产生数据库文件
3. 单例一旦创建，配置不可更改

## 解决方案

### 方案概述

**核心思路**：
1. **延迟引擎创建**：数据库文件只在首次访问时才创建
2. **配置可更新**：允许在应用启动时更新配置

### 具体实现

#### 1. 修改 DatabaseManager 类

```python
# database.py

class DatabaseManager:
    """数据库管理器（单例）
    
    支持延迟引擎创建和配置更新，解决导入顺序导致的多数据库文件问题。
    """
    _instance: Optional["DatabaseManager"] = None

    def __new__(cls, db_config: Optional[DatabaseConfig] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """初始化数据库管理器
        
        Args:
            db_config: 数据库配置，首次传入会保存，后续传入会更新
        """
        # 避免重复初始化
        if self._initialized:
            # 如果传入了新配置，更新配置并重置引擎
            if db_config is not None:
                self.db_config = db_config
                self._engine = None  # 重置引擎，下次访问时重新创建
            return

        self.db_config = db_config or default_config
        self._engine = None  # 延迟创建引擎
        self._initialized = True

    def set_config(self, db_config: DatabaseConfig) -> None:
        """更新数据库配置
        
        在应用启动时调用，确保使用正确的配置。
        配置更新后，下次访问引擎时会使用新配置创建引擎。
        
        Args:
            db_config: 新的数据库配置
            
        Example:
            >>> db = DatabaseManager()
            >>> db.set_config(DatabaseConfig(db_name="myapp.db"))
        """
        self.db_config = db_config
        self._engine = None  # 重置引擎，下次访问时重新创建

    @property
    def engine(self):
        """获取数据库引擎（延迟创建）
        
        首次访问时创建引擎，确保配置已经设置。
        """
        if self._engine is None:
            self._engine = create_engine(
                self.db_config.database_url,
                echo=False,
                connect_args={"check_same_thread": False},
                pool_size=5,
                max_overflow=10,
            )
            # 启用外键约束
            @event.listens_for(self._engine, "connect")
            def enable_foreign_keys(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")
                cursor.close()
        return self._engine

    def get_session(self):
        """获取数据库会话上下文管理器"""
        return Session(self.engine)
```

#### 2. 修改 DatabaseInitializer 类（同样延迟引擎创建）

```python
# database.py

class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        self.db_config = db_config or default_config
        self._engine = None  # 延迟创建

    def get_engine(self):
        """获取数据库引擎（延迟创建）"""
        if self._engine is None:
            self._engine = create_engine(
                self.db_config.database_url,
                echo=False,
                connect_args={"check_same_thread": False},
            )
        return self._engine

    def init_database(self, engine=None) -> None:
        """初始化数据库"""
        # 确保目录存在
        self.db_config.ensure_directory()
        
        # 创建引擎（如果未提供）
        if engine is None:
            engine = self.get_engine()
        
        # 创建表
        SQLModel.metadata.create_all(bind=engine)
```

#### 3. 可选：移除模块级 db 实例

```python
# database.py

# 删除模块级实例，避免导入时自动创建
# db = DatabaseManager()  # 删除这行

# 如果需要保持向后兼容，可以保留但注释掉
# db = None  # 由用户在应用启动时创建
```

### 用户使用方式

```python
# main.py
import sys
from PyQt5.QtWidgets import QApplication

# 1. 正常导入（导入顺序不再重要）
from app.view.main_window import MainWindow
from app.data.database import DatabaseManager, init_database
from app.data.config import DatabaseConfig
from app.common.config import cfg


def main():
    app = QApplication(sys.argv)
    
    # 2. 在应用启动时设置配置
    db_config = DatabaseConfig(
        db_name=cfg.get(cfg.dbName),  # "fpdcm.db"
        db_dir=cfg.get(cfg.dbPath),
    )
    
    # 方式A：使用 set_config 更新单例配置
    db = DatabaseManager()
    db.set_config(db_config)
    
    # 方式B：重新传入配置（效果相同）
    # db = DatabaseManager(db_config)
    
    # 3. 初始化数据库（创建表）
    init_database(db_config)
    
    # 4. 正常使用
    window = MainWindow()
    window.show()
    
    app.exec()


if __name__ == "__main__":
    main()
```

### 关键改进点

| 改进项 | 原实现 | 新实现 |
|--------|--------|--------|
| 引擎创建时机 | `__init__` 中立即创建 | 首次访问 `engine` 属性时创建 |
| 配置更新 | 不支持 | 支持 `set_config` 方法 |
| 导入顺序要求 | 必须在其他导入前设置配置 | 导入顺序无关 |
| 代码组织 | 需要在模块级别跑代码 | 所有配置在 `main()` 中完成 |

## 向后兼容说明

### 对于现有用户

如果用户没有自定义数据库配置，使用默认配置，无需修改代码。

### 对于需要自定义配置的用户

**旧代码**（需要特定导入顺序）：
```python
# 必须在其他导入前设置
db_config = DatabaseConfig(db_name="myapp.db")
init_database(db_config)

from app.view.main_window import MainWindow  # 导入必须在设置之后
```

**新代码**（导入顺序无关）：
```python
# 导入顺序不再重要
from app.view.main_window import MainWindow
from app.data.database import DatabaseManager

def main():
    # 在应用启动时设置配置
    db = DatabaseManager()
    db.set_config(DatabaseConfig(db_name="myapp.db"))
    
    # 正常使用
    window = MainWindow()
```

## 测试验证

### 测试场景 1：导入顺序无关

```python
# 先导入视图
from app.view.main_window import MainWindow

# 后设置配置
from app.data.database import DatabaseManager
db = DatabaseManager()
db.set_config(DatabaseConfig(db_name="test.db"))

# 验证只创建一个数据库文件
# 预期：只有 test.db，没有 app.db
```

### 测试场景 2：配置更新

```python
# 首次创建使用默认配置
db = DatabaseManager()
assert db.db_config.db_name == "app.db"

# 更新配置
db.set_config(DatabaseConfig(db_name="new.db"))
assert db.db_config.db_name == "new.db"

# 访问引擎时会使用新配置
engine = db.engine  # 创建 new.db，不创建 app.db
```

## 总结

通过**延迟引擎创建**和**配置可更新**，解决了 sqlmodel_crud 生成代码中的数据库配置问题：

1. **问题**：导入顺序导致单例在配置设置前创建，产生多数据库文件
2. **方案**：延迟引擎创建到首次访问时，允许应用启动时更新配置
3. **收益**：导入顺序无关，代码组织更清晰，符合 PyQt 编程习惯
