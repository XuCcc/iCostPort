"""多文件解析结果合并为单一列表。"""

from __future__ import annotations

from icostport.core.model import Transaction


def merge_lists(partitions: list[list[Transaction]]) -> list[Transaction]:
    """
    将多段 ``list[Transaction]`` 顺序拼接为单一列表（保持各段内部顺序）。
    """
    out: list[Transaction] = []
    for part in partitions:
        out.extend(part)
    return out
