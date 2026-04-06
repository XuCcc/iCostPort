"""ICost 导入行结构，与模板表头顺序一致。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from icostport.core.model import Transaction

# 与仓库根 ``icost_template.xlsx`` 第 1 行一致（权威列序）
ICOST_HEADERS: tuple[str, ...] = (
    "日期",
    "类型",
    "金额",
    "一级分类",
    "二级分类",
    "账户1",
    "账户2",
    "备注",
    "货币",
    "标签",
)


@dataclass
class ICostRow:
    """工作表单行，对应 A:J 列。"""

    date_display: str
    txn_type: str
    amount: Decimal
    primary: str
    secondary: str
    account1: str
    account2: str
    note: str
    currency: str
    tags: str


def format_icost_datetime(dt: datetime) -> str:
    """格式示例：``2011年01月11日 12:00:00``。"""
    return dt.strftime("%Y年%m月%d日 %H:%M:%S")


def transaction_to_icost_row(tx: Transaction) -> ICostRow:
    """将领域模型映射为 ICost 行（分类列来自 rules/AI 或空串）。"""
    return ICostRow(
        date_display=format_icost_datetime(tx.occurred_at),
        txn_type=tx.txn_type,
        amount=tx.amount,
        primary=tx.primary_category or "",
        secondary=tx.secondary_category or "",
        account1=tx.account1,
        account2=tx.account2,
        note=tx.note,
        currency=tx.currency,
        tags=tx.tags,
    )
