"""路径解析辅助模块"""

import re
from pathlib import Path
from typing import Optional


class PathResolver:
    """路径解析器类"""

    CRUD_SUBDIR = "crud"
    MODELS_SUBDIR = "models"

    def __init__(self, models_path: str, output_dir: str):
        """初始化路径解析器"""
        self.models_path = Path(models_path).resolve()
        self.output_dir = Path(output_dir).resolve()

        self._validate_models_path()
        self._validate_output_dir()
        self._check_path_conflict()

    def _validate_models_path(self) -> None:
        """验证模型路径"""

        original_path = str(self.models_path)
        if "." in original_path and not original_path.startswith("."):

            parts = (
                original_path.split("/")
                if "/" in original_path
                else original_path.split("\\")
            )
            if any("." in part and not part.startswith(".") for part in parts):
                raise ValueError(
                    f"模型路径不能使用模块导入格式: {original_path}\n"
                    f"请使用文件路径格式，例如: {original_path.replace('.', '/')}"
                )

        if not self.models_path.exists():
            raise ValueError(f"模型路径不存在: {self.models_path}")

        if not self.models_path.is_dir():
            raise ValueError(f"模型路径必须是目录: {self.models_path}")

    def _validate_output_dir(self) -> None:
        """验证输出目录"""
        if self.output_dir.exists() and not self.output_dir.is_dir():
            raise ValueError(f"输出路径必须是目录: {self.output_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _check_path_conflict(self) -> None:
        """检查模型路径和输出目录是否存在冲突"""
        try:

            self.models_path.relative_to(self.output_dir)
        except ValueError:

            return

        raise ValueError(
            f"模型路径不能位于输出目录内\n"
            f"  模型路径: {self.models_path}\n"
            f"  输出目录: {self.output_dir}\n"
            f"建议修改配置，确保两者不重叠，例如:\n"
            f"  - models_path='app/data/models', output_dir='app/generated'\n"
            f"  - models_path='models', output_dir='app/data'"
        )

    def get_models_path(self) -> Path:
        """获取模型路径"""
        return self.models_path

    def get_output_dir(self) -> Path:
        """获取输出目录"""
        return self.output_dir

    def get_crud_output_dir(self) -> Path:
        """获取 CRUD 代码输出目录"""
        return self.output_dir / self.CRUD_SUBDIR

    def get_models_output_dir(self) -> Path:
        """获取模型复制输出目录"""
        return self.output_dir / self.MODELS_SUBDIR

    def get_output_path(self, generator_type: str, model_name: str) -> Path:
        """获取输出文件路径"""
        snake_name = self._to_snake_case(model_name)

        if generator_type == "crud":
            subdir = self.CRUD_SUBDIR
        else:
            raise ValueError(f"无效的生成器类型: {generator_type}，可选值: crud")

        return self.output_dir / subdir / f"{snake_name}.py"

    def get_data_layer_db_path(self, db_name: str) -> Path:
        """获取数据层数据库文件路径"""
        return self.output_dir / db_name

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """将字符串转换为蛇形命名（snake_case）"""

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @classmethod
    def check_path_conflict(cls, models_path: str, output_dir: str) -> Optional[str]:
        """检查路径冲突（静态方法，用于预检查）"""
        models = Path(models_path).resolve()
        output = Path(output_dir).resolve()

        try:
            models.relative_to(output)
            return (
                f"模型路径不能位于输出目录内\n"
                f"  模型路径: {models}\n"
                f"  输出目录: {output}"
            )
        except ValueError:
            return None
