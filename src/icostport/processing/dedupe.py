"""按「日历日 + 金额」去重；策略可配置。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable, Iterable

from icostport.core.model import Transaction

# 去重键：日期（天） + 金额（统一量化到分）
DedupeKey = tuple[date, Decimal]


def _quantize_amount(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))


def _dedupe_key(tx: Transaction) -> DedupeKey:
    day = tx.occurred_at.date()
    return (day, _quantize_amount(tx.amount))


def dedupe_transactions(
    transactions: list[Transaction],
    *,
    on_duplicate: str = "keep_first",
    key_fn: Callable[[Transaction], DedupeKey] | None = None,
) -> list[Transaction]:
    """
    去除重复交易。默认键为「发生日（按天）+ 金额（两位小数）」。

    ``on_duplicate``：``keep_first`` 保留先出现的记录；``keep_last`` 保留后出现。
    """
    if key_fn is None:
        key_fn = _dedupe_key

    if on_duplicate not in ("keep_first", "keep_last"):
        raise ValueError(f"不支持的 on_duplicate: {on_duplicate}")

    if on_duplicate == "keep_first":
        return _dedupe_keep_first(transactions, key_fn)

    return _dedupe_keep_last(transactions, key_fn)


def _dedupe_keep_first(
    transactions: Iterable[Transaction],
    key_fn: Callable[[Transaction], DedupeKey],
) -> list[Transaction]:
    seen: set[DedupeKey] = set()
    out: list[Transaction] = []
    for tx in transactions:
        k = key_fn(tx)
        if k in seen:
            continue
        seen.add(k)
        out.append(tx)
    return out


def _dedupe_keep_last(
    transactions: Iterable[Transaction],
    key_fn: Callable[[Transaction], DedupeKey],
) -> list[Transaction]:
    # 逆序扫描，保留每个键第一次遇到（即原序列中最后一次）
    seen: set[DedupeKey] = set()
    out_rev: list[Transaction] = []
    for tx in reversed(list(transactions)):
        k = key_fn(tx)
        if k in seen:
            continue
        seen.add(k)
        out_rev.append(tx)
    return list(reversed(out_rev))
