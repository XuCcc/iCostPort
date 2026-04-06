"""金额区间、关键字等过滤（配置驱动）。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from icostport.core.model import Transaction


def apply_filters(
    transactions: list[Transaction],
    filter_cfg: dict[str, Any] | None,
) -> list[Transaction]:
    """
    根据 ``processing.filter`` 配置过滤交易。
    支持：``min_amount`` / ``max_amount``、``note_contains`` / ``note_excludes``（子串，大小写不敏感）。
    """
    if not filter_cfg:
        return list(transactions)

    min_a = filter_cfg.get("min_amount")
    max_a = filter_cfg.get("max_amount")
    includes = filter_cfg.get("note_contains") or []
    excludes = filter_cfg.get("note_excludes") or []

    if not isinstance(includes, list):
        includes = []
    if not isinstance(excludes, list):
        excludes = []

    includes_l = [str(x).lower() for x in includes]
    excludes_l = [str(x).lower() for x in excludes]

    out: list[Transaction] = []
    for tx in transactions:
        if min_a is not None and tx.amount < Decimal(str(min_a)):
            continue
        if max_a is not None and tx.amount > Decimal(str(max_a)):
            continue
        note_l = tx.note.lower()
        if includes_l and not any(s in note_l for s in includes_l):
            continue
        if excludes_l and any(s in note_l for s in excludes_l):
            continue
        out.append(tx)
    return out
