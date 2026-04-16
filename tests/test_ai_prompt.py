"""AI 分类 Prompt 模板读取测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from icostport.categorize.ai_categorize import _build_prompt, _load_prompt_template
from icostport.core.model import Transaction
from icostport.core.settings import AIConfig, ProcessingConfig, RuleConfig, Settings


def test_load_ai_prompt_template_contains_sections() -> None:
    templates = _load_prompt_template()

    assert "system" in templates
    assert "user" in templates
    assert "严谨的账单分类助手" in templates["system"]
    assert "{taxonomy}" in templates["user"]
    assert "{transactions}" in templates["user"]


def test_build_prompt_renders_transaction_list() -> None:
    tx = Transaction(
        occurred_at=datetime(2026, 1, 1, 12, 0, 0),
        amount=Decimal("30.00"),
        txn_type="支出",
        note="测试交易",
    )
    settings = Settings(
        categories={"餐饮": ["三餐"]},
        processing=ProcessingConfig(),
        rules=[RuleConfig(keywords=["测试"], primary="餐饮", secondary="三餐")],
        ai=AIConfig(enabled=True),
        config_path=None,
        raw={},
    )
    messages = _build_prompt([tx], settings)

    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert "严谨的账单分类助手" in messages[0]["content"]
    assert "+ 0.00" not in messages[1]["content"]
    assert "测试交易" in messages[1]["content"]


def test_run_ai_categorize_processes_all_unclassified_in_batches(monkeypatch) -> None:
    from icostport.categorize.ai_categorize import AIClient, run_ai_categorize

    txs = [
        Transaction(
            occurred_at=datetime(2026, 1, 1, 10, 0, 0),
            amount=Decimal("10.00"),
            txn_type="支出",
            note="交易1",
        ),
        Transaction(
            occurred_at=datetime(2026, 1, 1, 11, 0, 0),
            amount=Decimal("20.00"),
            txn_type="支出",
            note="交易2",
        ),
        Transaction(
            occurred_at=datetime(2026, 1, 1, 12, 0, 0),
            amount=Decimal("30.00"),
            txn_type="支出",
            note="交易3",
        ),
    ]
    settings = Settings(
        categories={},
        processing=ProcessingConfig(),
        rules=[],
        ai=AIConfig(enabled=True, only_if_uncategorized=True, max_items=2),
        config_path=None,
        raw={},
    )

    responses = iter([
        '[{"index": 0, "primary": "A", "secondary": "a"}, {"index": 1, "primary": "B", "secondary": "b"}]',
        '[{"index": 0, "primary": "C", "secondary": "c"}]',
    ])

    def fake_chat_completion(self, messages, timeout=None):
        return next(responses, "")

    monkeypatch.setattr(AIClient, "chat_completion", fake_chat_completion)

    assigned = run_ai_categorize(txs, settings, verbose=False)

    assert assigned == 3
    assert txs[0].primary_category == "A"
    assert txs[1].primary_category == "B"
    assert txs[2].primary_category == "C"
