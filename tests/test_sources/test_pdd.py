"""拼多多账单解析器测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from icostport.core.model import Transaction
from icostport.sources import parse_path
from icostport.sources import registry


def test_parse_pdd_sample(fixtures_dir: Path) -> None:
    path = fixtures_dir / "PDD_用户_0865_筛选结果_sample.csv"
    txs = parse_path(path)

    assert len(txs) == 1
    txn = txs[0]

    assert txn.occurred_at == datetime(2026, 3, 23, 23, 40)
    assert txn.amount == Decimal("24.44")
    assert txn.txn_type == "支出"
    assert "小亿汽车用品官方旗舰店" in txn.note
    assert txn.account1 == "云闪付"
    assert txn.source_path == path


def test_parse_pdd_skips_invalid_rows(tmp_path: Path) -> None:
    path = tmp_path / "PDD_test.csv"
    path.write_text(
        "订单号,时间,店铺,商品,规格,数量,支付方式,实付,状态,链接\n"
        "1,2026/03/23 12:00,店铺A,商品A,规格A,1,微信支付,12.34,已完成,https://example.com\n"
        "2,2026/03/23 13:00,店铺B,商品B,规格B,1,云闪付,abc,已完成,https://example.com\n"
        "3,,店铺C,商品C,规格C,1,支付宝,45.67,已完成,https://example.com\n",
        encoding="utf-8-sig",
    )

    parser = registry.resolve_parser(path)
    assert parser is not None
    txs = parser(path)

    assert len(txs) == 1
    assert txs[0].amount == Decimal("12.34")
    assert txs[0].txn_type == "支出"


def test_pdd_filename_detector_matches(tmp_path: Path) -> None:
    path = tmp_path / "PDD_order_list.csv"
    path.write_text(
        "订单号,时间,店铺,商品,规格,数量,支付方式,实付,状态,链接\n"
        "1,2026/03/23 12:00,店铺A,商品A,规格A,1,微信支付,12.34,已完成,https://example.com\n",
        encoding="utf-8-sig",
    )

    parser = registry.resolve_parser(path)
    assert parser is not None
    txs = parser(path)
    assert len(txs) == 1
    assert txs[0].amount == Decimal("12.34")
