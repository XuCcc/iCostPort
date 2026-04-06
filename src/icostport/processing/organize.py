"""排序、分组视图等整理步骤（当前仅实现按时间排序）。"""

from __future__ import annotations

from icostport.core.model import Transaction


def sort_by_time(
    transactions: list[Transaction], *, reverse: bool = False
) -> list[Transaction]:
    """按 ``occurred_at`` 排序。"""
    return sorted(transactions, key=lambda t: t.occurred_at, reverse=reverse)
