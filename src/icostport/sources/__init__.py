"""各银行/导出格式解析器与注册表。导入子模块以完成内置注册。"""

from . import example_csv  # noqa: F401
from icostport.sources.registry import parse_path, register_parser

__all__ = ["example_csv", "parse_path", "register_parser"]
