"""变更检测器模块。"""

import json
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .scanner import ModelMeta, FieldMeta
from .exceptions import DatabaseError


class ChangeType(str, Enum):
    """变更类型枚举"""

    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


@dataclass
class ModelChange:
    """模型变更信息。"""

    change_type: ChangeType
    model_name: str
    field_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str = ""


class DateTimeEncoder(json.JSONEncoder):
    """自定义 JSON 编码器"""

    def default(self, obj: Any) -> Any:
        """处理特殊类型的序列化"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()

        if type(obj).__name__ == "PydanticUndefinedType":
            return None

        if callable(obj):
            return obj.__name__ if hasattr(obj, "__name__") else str(obj)
        return super().default(obj)


class ChangeDetector:
    """变更检测器类。"""

    def __init__(self, snapshot_file: str):
        """初始化变更检测器。"""
        self.snapshot_file = snapshot_file
        self.snapshot: Dict[str, Any] = {}
        self.load_snapshot()

    def load_snapshot(self) -> Dict[str, Any]:
        """加载上次的模型快照。"""
        snapshot_path = Path(self.snapshot_file)
        if snapshot_path.exists():
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    self.snapshot = json.load(f)
            except (json.JSONDecodeError, IOError) as e:

                backup_path = snapshot_path.with_suffix(".json.bak")
                snapshot_path.replace(backup_path)
                print(f"[提示] 快照文件损坏，已备份到: {backup_path}")
                print(f"[提示] 将重新生成所有代码")
                self.snapshot = {}
        else:
            self.snapshot = {}
        return self.snapshot

    def save_snapshot(self, models: List[ModelMeta]) -> None:
        """保存当前模型快照到文件。"""
        snapshot_data = {}
        for model in models:
            snapshot_data[model.name] = self._model_to_dict(model)

        snapshot_path = Path(self.snapshot_file)
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(
                    snapshot_data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder
                )
        except IOError as e:
            raise DatabaseError(
                f"无法保存快照文件: {e}",
                operation="save",
                context={"file_path": str(snapshot_path)},
            ) from e

    def detect_changes(self, current_models: List[ModelMeta]) -> List[ModelChange]:
        """检测当前模型与上次快照的差异。"""
        changes: List[ModelChange] = []

        current_model_names = {model.name for model in current_models}
        snapshot_model_names = set(self.snapshot.keys())

        for model in current_models:
            if model.name not in self.snapshot:
                changes.append(
                    ModelChange(
                        change_type=ChangeType.ADDED,
                        model_name=model.name,
                        description=f"新增模型: {model.name}",
                    )
                )
            else:

                old_model = self.snapshot[model.name]
                model_changes = self._compare_model(old_model, model)
                changes.extend(model_changes)

        for removed_name in snapshot_model_names - current_model_names:
            changes.append(
                ModelChange(
                    change_type=ChangeType.REMOVED,
                    model_name=removed_name,
                    description=f"删除模型: {removed_name}",
                )
            )

        return changes

    def _compare_model(
        self, old_model: Dict[str, Any], new_model: ModelMeta
    ) -> List[ModelChange]:
        """比较单个模型的差异。"""
        changes: List[ModelChange] = []

        old_fields = {f["name"]: f for f in old_model.get("fields", [])}
        new_fields = {f.name: f for f in new_model.fields}

        old_field_names = set(old_fields.keys())
        new_field_names = set(new_fields.keys())

        for field_name in new_field_names - old_field_names:
            changes.append(
                ModelChange(
                    change_type=ChangeType.ADDED,
                    model_name=new_model.name,
                    field_name=field_name,
                    new_value=new_fields[field_name].to_dict(),
                    description=f"模型 {new_model.name} 新增字段: {field_name}",
                )
            )

        for field_name in old_field_names - new_field_names:
            changes.append(
                ModelChange(
                    change_type=ChangeType.REMOVED,
                    model_name=new_model.name,
                    field_name=field_name,
                    old_value=old_fields[field_name],
                    description=f"模型 {new_model.name} 删除字段: {field_name}",
                )
            )

        for field_name in old_field_names & new_field_names:
            field_changes = self._compare_field(
                old_fields[field_name], new_fields[field_name]
            )
            changes.extend(field_changes)

        old_table_name = old_model.get("table_name")
        if old_table_name != new_model.table_name:
            changes.append(
                ModelChange(
                    change_type=ChangeType.MODIFIED,
                    model_name=new_model.name,
                    old_value=old_table_name,
                    new_value=new_model.table_name,
                    description=f"模型 {new_model.name} 表名变更: {old_table_name} -> {new_model.table_name}",
                )
            )

        old_primary_keys = set(old_model.get("primary_keys", []))
        new_primary_keys = set(new_model.primary_keys)
        if old_primary_keys != new_primary_keys:
            changes.append(
                ModelChange(
                    change_type=ChangeType.MODIFIED,
                    model_name=new_model.name,
                    old_value=list(old_primary_keys),
                    new_value=list(new_primary_keys),
                    description=f"模型 {new_model.name} 主键变更: {old_primary_keys} -> {new_primary_keys}",
                )
            )

        return changes

    def _compare_field(
        self, old_field: Dict[str, Any], new_field: FieldMeta
    ) -> List[ModelChange]:
        """比较单个字段的差异。"""
        changes: List[ModelChange] = []
        new_field_dict = new_field.to_dict()

        compare_attrs = [
            "field_type",
            "nullable",
            "primary_key",
            "default",
            "foreign_key",
            "unique",
            "index",
            "max_length",
            "description",
        ]

        for attr in compare_attrs:
            old_value = old_field.get(attr)
            new_value = new_field_dict.get(attr)

            old_str = str(old_value) if old_value is not None else ""
            new_str = str(new_value) if new_value is not None else ""
            if "PydanticUndefined" in old_str or "PydanticUndefined" in new_str:
                continue

            if old_value != new_value:
                changes.append(
                    ModelChange(
                        change_type=ChangeType.MODIFIED,
                        model_name=new_field_dict.get("name", ""),
                        field_name=new_field.name,
                        old_value=old_value,
                        new_value=new_value,
                        description=f"字段 {new_field.name}.{attr} 变更: {old_value} -> {new_value}",
                    )
                )

        return changes

    def has_changes(self, current_models: List[ModelMeta]) -> bool:
        """快速检查是否有变更。"""
        return len(self.detect_changes(current_models)) > 0

    def get_summary(self, changes: List[ModelChange]) -> str:
        """生成变更摘要报告。"""
        if not changes:
            return "没有检测到变更"

        added = [
            c
            for c in changes
            if c.change_type == ChangeType.ADDED and c.field_name is None
        ]
        removed = [
            c
            for c in changes
            if c.change_type == ChangeType.REMOVED and c.field_name is None
        ]
        modified = [
            c
            for c in changes
            if c.change_type == ChangeType.MODIFIED and c.field_name is None
        ]

        field_added = [
            c
            for c in changes
            if c.change_type == ChangeType.ADDED and c.field_name is not None
        ]
        field_removed = [
            c
            for c in changes
            if c.change_type == ChangeType.REMOVED and c.field_name is not None
        ]
        field_modified = [
            c
            for c in changes
            if c.change_type == ChangeType.MODIFIED and c.field_name is not None
        ]

        lines = ["=" * 50, "变更检测摘要", "=" * 50]

        if added:
            lines.append(f"\n[新增模型] ({len(added)}个):")
            for c in added:
                lines.append(f"  + {c.model_name}")

        if removed:
            lines.append(f"\n[删除模型] ({len(removed)}个):")
            for c in removed:
                lines.append(f"  - {c.model_name}")

        if modified:
            lines.append(f"\n[修改模型] ({len(modified)}个):")
            for c in modified:
                lines.append(f"  ~ {c.model_name}: {c.description}")

        if field_added:
            lines.append(f"\n[新增字段] ({len(field_added)}个):")
            for c in field_added:
                lines.append(f"  + {c.model_name}.{c.field_name}")

        if field_removed:
            lines.append(f"\n[删除字段] ({len(field_removed)}个):")
            for c in field_removed:
                lines.append(f"  - {c.model_name}.{c.field_name}")

        if field_modified:
            lines.append(f"\n[修改字段] ({len(field_modified)}个):")
            for c in field_modified:
                lines.append(f"  ~ {c.description}")

        lines.append(f"\n{'=' * 50}")
        lines.append(f"总计: {len(changes)} 处变更")

        return "\n".join(lines)

    def _model_to_dict(self, model: ModelMeta) -> Dict[str, Any]:
        """将模型元数据转换为字典。"""
        return {
            "name": model.name,
            "table_name": model.table_name,
            "fields": [f.to_dict() for f in model.fields],
            "primary_keys": model.primary_keys,
            "foreign_keys": model.foreign_keys,
            "indexes": model.indexes,
            "unique_constraints": model.unique_constraints,
            "description": model.description,
            "is_table": model.is_table,
        }

    def clear_snapshot(self) -> None:
        """清除快照文件。"""
        self.snapshot = {}
        snapshot_path = Path(self.snapshot_file)
        if snapshot_path.exists():
            try:
                snapshot_path.unlink()
            except IOError as e:
                raise DatabaseError(
                    f"无法删除快照文件: {e}",
                    operation="clear",
                    context={"file_path": str(snapshot_path)},
                ) from e
