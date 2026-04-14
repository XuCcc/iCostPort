"""支付宝记账单解析器测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from icostport.sources.alipay import detect_alipay_by_content, parse_alipay


@pytest.fixture
def alipay_fixture() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "支付宝记账单_sample.csv"


def test_detect_by_content(alipay_fixture: Path) -> None:
    assert detect_alipay_by_content(alipay_fixture)


def test_parse_basic(alipay_fixture: Path) -> None:
    txns = parse_alipay(alipay_fixture)
    assert len(txns) == 1


def test_parse_fields(alipay_fixture: Path) -> None:
    txns = parse_alipay(alipay_fixture)
    txn = txns[0]

    assert txn.occurred_at == datetime(2026, 3, 29, 20, 10)
    assert txn.amount == Decimal("3")
    assert txn.txn_type == "支出"
    assert "地铁_北太平庄" in txn.note
    assert txn.account1 == "招商银行"
    assert txn.currency == "CNY"


def test_parse_skip_empty_rows(tmp_path: Path) -> None:
    path = tmp_path / "alipay_skip.csv"
    path.write_text(
        "特别提示：\n"
        "1.本记账单内容可表明支付宝受理了相应记账明细申请，因系统原因或通讯故障等偶发因素导致本记账单与实际记账结果不符时，以实际记账情况为准；\n"
        "记录时间,分类,收支类型,金额,备注,账户,来源,标签\n"
        "2026/3/29 20:10,交通,支出,3,测试备注,招商银行,账单同步,\n"
        ",,,,,,,\n",
        encoding="utf-8",
    )

    txns = parse_alipay(path)
    assert len(txns) == 1
    assert txns[0].note == "测试备注 账单同步"


def test_registry_detects_alipay(alipay_fixture: Path) -> None:
    from icostport.sources.registry import resolve_parser

    parser = resolve_parser(alipay_fixture)
    assert parser is not None
    assert parser == parse_alipay
