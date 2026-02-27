# 更新日志

所有项目的显著变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.1.0] - 2026-02-27

### 重大变更 (Breaking Changes)

- **移除配置项**：
  - 移除 `crud_output_dir` 配置项
  - 移除 `schemas_output_dir` 配置项
  - 移除 `data_layer_db_dir` 配置项
- **简化模型路径配置**：
  - `models_path` 仅支持文件路径格式（如 `app/models`）
  - 不再支持模块导入路径格式（如 `app.models`）

### 新增

- 添加 `PathResolver` 路径解析辅助类，集中处理所有路径相关逻辑
- 添加路径冲突自动检测和处理机制

### 改进

- **输出目录结构固定化**：
  - `crud/` - CRUD 代码输出目录
  - `schemas/` - Schema 代码输出目录
  - `models/` - 模型复制目录（可选）
- **路径冲突智能处理**：
  - 当 `models_path` 位于 `output_dir` 内时，自动禁用模型复制
  - 避免生成两份模型文件的问题
- **配置验证优化**：
  - 配置创建时立即验证所有路径
  - 移除延迟验证机制，错误更早暴露
- **简化配置模块**：
  - 减少配置项数量，降低用户使用复杂度
  - 使用 `DEFAULT_CONFIG_DICT` 替代 `DEFAULT_CONFIG` 常量

### 迁移指南

**从 v1.x 迁移到 v2.0**：

1. **更新配置文件**：
   ```toml
   # 旧配置
   [sqlmodel-crud]
   models_path = "app.models"  # ❌ 不再支持
   crud_output_dir = "crud"     # ❌ 已移除
   schemas_output_dir = "schemas"  # ❌ 已移除
   data_layer_db_dir = "data"   # ❌ 已移除
   
   # 新配置
   [sqlmodel-crud]
   models_path = "app/models"   # ✅ 使用文件路径
   # crud_output_dir 等配置项已移除，使用固定结构
   ```

2. **路径冲突处理**：
   - 如果 `models_path` 位于 `output_dir` 内，系统会自动禁用模型复制
   - 无需手动设置 `generate_model_copy = false`

## [1.0.0.0] - 2026-03-14

### 新增
- 完整的 CRUD 基类实现（同步和异步）
- 软删除和恢复功能支持
- 数据库连接管理器（支持 SQLite、PostgreSQL、MySQL）
- 代码生成器，可根据 SQLModel 模型自动生成 CRUD 代码
- 模型扫描器，自动提取模型元数据
- 变更检测器，跟踪模型变化
- 完整的配置管理系统
- 命令行接口（CLI）
- 统一的异常处理机制
- 完整的类型注解支持

### 功能特性
- 支持分页查询、过滤和排序
- 支持批量创建记录
- 支持存在性检查和计数
- 支持外键关系处理
- 支持自定义模板
- 支持增量代码生成

### 测试
- 140 个单元测试，覆盖率 100%
- 支持同步和异步测试
- 完整的边界条件测试



---

## 版本说明

- **主版本号**：不兼容的 API 更改
- **次版本号**：向下兼容的功能添加
- **修订号**：向下兼容的问题修复
