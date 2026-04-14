"""分类规则 Tags 行为测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from icostport.categorize.rules import apply_keyword_rules
from icostport.core.model import Transaction
from icostport.core.settings import AIConfig, ProcessingConfig, RuleConfig, Settings


def test_apply_keyword_rules_accumulates_tags_and_assigns_category() -> None:
    tx = Transaction(
        occurred_at=datetime(2026, 1, 1, 12, 0, 0),
        amount=Decimal("30.00"),
        txn_type="支出",
        note="滴滴打车，欢迎体验",
    )
    settings = Settings(
        categories={"交通": ["打车"]},
        processing=ProcessingConfig(),
        rules=[
            RuleConfig(
                keywords=["滴滴"],
                primary="交通",
                secondary="打车",
                tags=["A", "B"],
            ),
            RuleConfig(
                keywords=["打车"],
                primary="交通",
                secondary="打车",
                tags=["B", "C"],
            ),
        ],
        ai=AIConfig(),
        config_path=None,
        raw={},
    )

    apply_keyword_rules([tx], settings)

    assert tx.primary_category == "交通"
    assert tx.secondary_category == "打车"
    assert tx.tags == "#A#B#C"
