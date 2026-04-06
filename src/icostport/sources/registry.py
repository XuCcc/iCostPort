"""按扩展名注册解析器，供流水线为每个输入路径选型。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from icostport.core.exceptions import ParserNotFoundError
from icostport.core.model import Transaction

ParserFn = Callable[[Path], list[Transaction]]

_REGISTRY: dict[str, ParserFn] = {}


def register_parser(ext: str, fn: ParserFn) -> None:
    """注册扩展名（不含点，小写），例如 ``csv``。"""
    key = ext.lower().lstrip(".")
    _REGISTRY[key] = fn


def parse_path(path: Path) -> list[Transaction]:
    """根据 ``path.suffix`` 选择解析器并解析。"""
    ext = path.suffix.lower().lstrip(".")
    if not ext or ext not in _REGISTRY:
        raise ParserNotFoundError(f"未注册扩展名 {ext!r}，无法解析: {path}")
    return _REGISTRY[ext](path)
