"""
路径解析器测试。
"""

from pathlib import Path

import pytest

from sqlmodel_crud.path_resolver import PathResolver


class TestPathResolverConflict:
    """测试路径冲突检测行为。"""

    def test_check_path_conflict_should_raise_when_models_inside_output(self, tmp_path):
        output_dir = tmp_path / "generated"
        models_dir = output_dir / "models"
        models_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="模型路径不能位于输出目录内"):
            PathResolver(models_path=str(models_dir), output_dir=str(output_dir))

    def test_check_path_conflict_static_method_returns_message(self, tmp_path):
        output_dir = tmp_path / "generated"
        models_dir = output_dir / "models"
        models_dir.mkdir(parents=True)

        message = PathResolver.check_path_conflict(
            models_path=str(models_dir),
            output_dir=str(output_dir),
        )

        assert message is not None
        assert "模型路径不能位于输出目录内" in message
        assert str(Path(models_dir).resolve()) in message
