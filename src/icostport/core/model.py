"""交易领域模型（与具体银行导出格式解耦）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional


@dataclass
class Transaction:
    """单条交易记录，供合并、去重、过滤与归类使用。"""

    occurred_at: datetime
    amount: Decimal
    txn_type: str  # 如：支出、收入、转账（与 ICost「类型」列一致）
    note: str = ""
    account1: str = ""
    account2: str = ""
    currency: str = "CNY"
    source_path: Path = field(default_factory=lambda: Path("."))
    # 归类结果；None 表示尚未归类，由 rules / AI 填充
    primary_category: Optional[str] = None
    secondary_category: Optional[str] = None
    tags: str = ""
    fingerprint: Optional[str] = None
