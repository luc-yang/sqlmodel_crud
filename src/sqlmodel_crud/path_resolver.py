"""
路径解析辅助模块

提供统一的路径解析和验证功能，集中处理所有路径相关逻辑。
"""

import re
from pathlib import Path
from typing import Optional


class PathResolver:
    """
    路径解析器类

    集中处理所有路径相关逻辑，包括：
    - 模型路径解析和验证
    - 输出路径生成
    - 路径冲突检测

    Attributes:
        models_path: 模型扫描路径
        output_dir: 代码输出目录
    """

    # 固定的输出子目录名称
    CRUD_SUBDIR = "crud"
    SCHEMAS_SUBDIR = "schemas"
    MODELS_SUBDIR = "models"

    def __init__(self, models_path: str, output_dir: str):
        """
        初始化路径解析器

        Args:
            models_path: 模型扫描路径
            output_dir: 代码输出目录

        Raises:
            ValueError: 当路径无效或存在冲突时抛出
        """
        self.models_path = Path(models_path).resolve()
        self.output_dir = Path(output_dir).resolve()

        # 立即验证路径
        self._validate_models_path()
        self._validate_output_dir()
        self._check_path_conflict()

    def _validate_models_path(self) -> None:
        """
        验证模型路径

        Raises:
            ValueError: 当路径不存在、不是目录或格式无效时抛出
        """
        # 检查是否为模块导入路径格式（包含点但不是以点开头）
        original_path = str(self.models_path)
        if "." in original_path and not original_path.startswith("."):
            # 进一步检查是否看起来像模块路径（如 app.models）
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
        """
        验证输出目录

        如果目录不存在，会自动创建

        Raises:
            ValueError: 当路径存在但不是目录时抛出
        """
        if self.output_dir.exists() and not self.output_dir.is_dir():
            raise ValueError(f"输出路径必须是目录: {self.output_dir}")

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _check_path_conflict(self) -> None:
        """
        检查模型路径和输出目录是否存在冲突

        如果模型路径位于输出目录内，会导致循环导入问题

        Raises:
            ValueError: 当检测到路径冲突时抛出
        """
        try:
            # 检查 models_path 是否是 output_dir 的子目录
            self.models_path.relative_to(self.output_dir)
            raise ValueError(
                f"模型路径不能位于输出目录内\n"
                f"  模型路径: {self.models_path}\n"
                f"  输出目录: {self.output_dir}\n"
                f"建议修改配置，确保两者不重叠，例如:\n"
                f"  - models_path='app/data/models', output_dir='app/generated'\n"
                f"  - models_path='models', output_dir='app/data'"
            )
        except ValueError:
            # relative_to 抛出 ValueError 表示不是子目录，这是正常情况
            pass

    def get_models_path(self) -> Path:
        """
        获取模型路径

        Returns:
            模型路径的 Path 对象
        """
        return self.models_path

    def get_output_dir(self) -> Path:
        """
        获取输出目录

        Returns:
            输出目录的 Path 对象
        """
        return self.output_dir

    def get_crud_output_dir(self) -> Path:
        """
        获取 CRUD 代码输出目录

        Returns:
            CRUD 输出目录的 Path 对象
        """
        return self.output_dir / self.CRUD_SUBDIR

    def get_schemas_output_dir(self) -> Path:
        """
        获取 Schemas 代码输出目录

        Returns:
            Schemas 输出目录的 Path 对象
        """
        return self.output_dir / self.SCHEMAS_SUBDIR

    def get_models_output_dir(self) -> Path:
        """
        获取模型复制输出目录

        Returns:
            模型复制输出目录的 Path 对象
        """
        return self.output_dir / self.MODELS_SUBDIR

    def get_output_path(self, generator_type: str, model_name: str) -> Path:
        """
        获取输出文件路径

        Args:
            generator_type: 生成器类型（crud/schemas）
            model_name: 模型名称

        Returns:
            输出文件的 Path 对象

        Raises:
            ValueError: 当生成器类型无效时抛出
        """
        snake_name = self._to_snake_case(model_name)

        if generator_type == "crud":
            subdir = self.CRUD_SUBDIR
        elif generator_type == "schemas":
            subdir = self.SCHEMAS_SUBDIR
        else:
            raise ValueError(
                f"无效的生成器类型: {generator_type}，可选值: crud, schemas"
            )

        return self.output_dir / subdir / f"{snake_name}.py"

    def get_data_layer_db_path(self, db_name: str) -> Path:
        """
        获取数据层数据库文件路径

        数据库文件直接放在 output_dir 下，不再创建 data/ 子目录

        Args:
            db_name: 数据库文件名

        Returns:
            数据库文件的 Path 对象
        """
        return self.output_dir / db_name

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """
        将字符串转换为蛇形命名（snake_case）

        Args:
            name: 原始字符串

        Returns:
            蛇形命名字符串
        """
        # 处理驼峰命名
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @classmethod
    def check_path_conflict(cls, models_path: str, output_dir: str) -> Optional[str]:
        """
        检查路径冲突（静态方法，用于预检查）

        Args:
            models_path: 模型扫描路径
            output_dir: 代码输出目录

        Returns:
            如果存在冲突，返回错误信息字符串；否则返回 None
        """
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
