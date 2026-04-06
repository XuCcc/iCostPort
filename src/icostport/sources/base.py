"""解析器协议：每种源格式实现 ``__call__(path) -> list[Transaction]``。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from icostport.core.model import Transaction


class BillParser(Protocol):
    """注册到 :mod:`icostport.sources.registry` 的解析器可调用对象。"""

    def __call__(self, path: Path) -> list[Transaction]:
        """解析单个源文件为交易列表。"""
        ...
