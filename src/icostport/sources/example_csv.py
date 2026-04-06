"""示例 CSV：列名固定，便于端到端打通与单测（非某银行真实导出）。"""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from icostport.core.model import Transaction
from icostport.sources.registry import register_parser


def _parse_datetime(value: str) -> datetime:
    s = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # 允许 ISO 8601
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_example_csv(path: Path) -> list[Transaction]:
    """
    读取首行为表头的 CSV。必填列：``date``, ``amount``, ``type``；
    可选：``note``, ``currency``, ``account1``, ``account2``。
    """
    out: list[Transaction] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return out
        fields = {h.strip().lower(): h for h in reader.fieldnames if h}

        def col(name: str) -> str | None:
            return fields.get(name.lower())

        c_date = col("date")
        c_amount = col("amount")
        c_type = col("type")
        if not c_date or not c_amount or not c_type:
            msg = "示例 CSV 需包含 date, amount, type 列"
            raise ValueError(msg)

        c_note = col("note")
        c_cur = col("currency")
        c_a1 = col("account1")
        c_a2 = col("account2")

        for row in reader:
            raw_amt = (row.get(c_amount) or "").strip()
            try:
                amount = Decimal(raw_amt)
            except InvalidOperation as e:
                raise ValueError(f"金额无效: {raw_amt!r}") from e

            raw_date = (row.get(c_date) or "").strip()
            if not raw_date:
                raise ValueError("date 列为空")

            tx = Transaction(
                occurred_at=_parse_datetime(raw_date),
                amount=amount,
                txn_type=(row.get(c_type) or "").strip() or "支出",
                note=(row.get(c_note) or "").strip() if c_note else "",
                account1=(row.get(c_a1) or "").strip() if c_a1 else "",
                account2=(row.get(c_a2) or "").strip() if c_a2 else "",
                currency=(row.get(c_cur) or "CNY").strip() if c_cur else "CNY",
                source_path=path,
            )
            out.append(tx)
    return out


register_parser("csv", parse_example_csv)
