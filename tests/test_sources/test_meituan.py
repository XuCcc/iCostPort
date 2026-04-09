"""美团账单解析器测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from icostport.sources.meituan import (
    detect_meituan_by_content,
    detect_meituan_by_name,
    parse_meituan,
)


@pytest.fixture
def meituan_fixture(tmp_path: Path) -> Path:
    """创建美团账单测试 fixture。"""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "美团账单_sample.csv"
    return fixture_path


class TestMeituanDetection:
    """美团账单检测测试。"""

    def test_detect_by_filename(self, meituan_fixture: Path) -> None:
        """通过文件名包含"美团"识别。"""
        assert detect_meituan_by_name(meituan_fixture)

    def test_detect_by_content(self, meituan_fixture: Path) -> None:
        """通过内容（第一行包含"美团"）识别。"""
        assert detect_meituan_by_content(meituan_fixture)

    def test_not_detected_by_unrelated_filename(self, tmp_path: Path) -> None:
        """不匹配无关文件名。"""
        path = tmp_path / "other_bank.csv"
        path.write_text("any content")
        assert not detect_meituan_by_name(path)


class TestMeituanParsing:
    """美团账单解析测试。"""

    def test_parse_basic(self, meituan_fixture: Path) -> None:
        """基本解析：行数与字段正确。"""
        txns = parse_meituan(meituan_fixture)
        assert len(txns) == 2

    def test_parse_fields(self, meituan_fixture: Path) -> None:
        """解析字段正确性。"""
        txns = parse_meituan(meituan_fixture)

        # 第一条交易
        assert txns[0].occurred_at == datetime(2026, 3, 31, 20, 58)
        assert txns[0].amount == Decimal("18.88")
        assert txns[0].txn_type == "支出"
        assert "测试商户1" in txns[0].note
        assert txns[0].currency == "CNY"

        # 第二条交易
        assert txns[1].occurred_at == datetime(2026, 3, 30, 12, 31)
        assert txns[1].amount == Decimal("18.88")
        assert txns[1].txn_type == "支出"
        assert "测试商户2" in txns[1].note

    def test_parse_amount_with_yuan_symbol(self, tmp_path: Path) -> None:
        """测试含¥符号的金额解析。"""
        path = tmp_path / "test_meituan.csv"
        content = """美团交易账单明细,,,,,,,,,,
美团用户名：[Test],,,,,,,,,,
起始时间：[2026-01-01] 终止时间：[2026-01-31],,,,,,,,,,
导出交易类型：[全部],,,,,,,,,,
导出时间：[2026-01-01 00:00:00],,,,,,,,,,
,,,,,,,,,,
共：1笔记录,,,,,,,,,,
支出：1笔 99.99元,,,,,,,,,,
收入：0笔 0.00元,,,,,,,,,,
不计收支：0笔 0.00元,,,,,,,,,,
,,,,,,,,,,
特别提示：,,,,,,,,,,
1. 本明细与实际交易结果不符时，以实际交易情况为准,,,,,,,,,,
2. 本明细仅展示当前账单中的交易，不包括已删除的记录,,,,,,,,,,
3. 部分账单记录如充值/提现等交易，不计入为收入或支出类别,,,,,,,,,,
4. 因统计逻辑不同，明细的实付金额累加后可能与统计金额不一致，请以实际交易金额为准,,,,,,,,,,
5. 本明细仅供用户个人对账使用，不具备任何证明效力，禁止用于非法用途,,,,,,,,,,
,,,,,,,,,,
【美团交易账单明细列表】,,,,,,,,,,
交易创建时间,交易成功时间,交易类型,订单标题,收/支,支付方式,订单金额,实付金额,交易单号,商家单号,备注
2026/1/15 10:00,2026/1/15 10:01,支付,Test Payment,支出,微信支付,¥99.99,¥99.99,ID001,MID001,/
"""
        path.write_text(content, encoding="utf-8")
        txns = parse_meituan(path)
        assert len(txns) == 1
        assert txns[0].amount == Decimal("99.99")

    def test_parse_skip_empty_rows(self, tmp_path: Path) -> None:
        """跳过空行。"""
        path = tmp_path / "test_meituan_empty.csv"
        content = """美团交易账单明细,,,,,,,,,,
美团用户名：[Test],,,,,,,,,,
起始时间：[2026-01-01] 终止时间：[2026-01-31],,,,,,,,,,
导出交易类型：[全部],,,,,,,,,,
导出时间：[2026-01-01 00:00:00],,,,,,,,,,
,,,,,,,,,,
共：1笔记录,,,,,,,,,,
支出：1笔 50.00元,,,,,,,,,,
收入：0笔 0.00元,,,,,,,,,,
不计收支：0笔 0.00元,,,,,,,,,,
,,,,,,,,,,
特别提示：,,,,,,,,,,
1. 本明细与实际交易结果不符时，以实际交易情况为准,,,,,,,,,,
2. 本明细仅展示当前账单中的交易，不包括已删除的记录,,,,,,,,,,
3. 部分账单记录如充值/提现等交易，不计入为收入或支出类别,,,,,,,,,,
4. 因统计逻辑不同，明细的实付金额累加后可能与统计金额不一致，请以实际交易金额为准,,,,,,,,,,
5. 本明细仅供用户个人对账使用，不具备任何证明效力，禁止用于非法用途,,,,,,,,,,
,,,,,,,,,,
【美团交易账单明细列表】,,,,,,,,,,
交易创建时间,交易成功时间,交易类型,订单标题,收/支,支付方式,订单金额,实付金额,交易单号,商家单号,备注
2026/1/15 10:00,2026/1/15 10:01,支付,Test,支出,微信支付,¥50.00,¥50.00,ID001,MID001,/
,,,,,,,,,,
,,,,,,,,,,
"""
        path.write_text(content, encoding="utf-8")
        txns = parse_meituan(path)
        assert len(txns) == 1
        assert txns[0].note == "Test"

    def test_parse_income_type(self, tmp_path: Path) -> None:
        """测试收入交易类型识别。"""
        path = tmp_path / "test_meituan_income.csv"
        content = """美团交易账单明细,,,,,,,,,,
美团用户名：[Test],,,,,,,,,,
起始时间：[2026-01-01] 终止时间：[2026-01-31],,,,,,,,,,
导出交易类型：[全部],,,,,,,,,,
导出时间：[2026-01-01 00:00:00],,,,,,,,,,
,,,,,,,,,,
共：1笔记录,,,,,,,,,,
支出：0笔 0.00元,,,,,,,,,,
收入：1笔 100.00元,,,,,,,,,,
不计收支：0笔 0.00元,,,,,,,,,,
,,,,,,,,,,
特别提示：,,,,,,,,,,
1. 本明细与实际交易结果不符时，以实际交易情况为准,,,,,,,,,,
2. 本明细仅展示当前账单中的交易，不包括已删除的记录,,,,,,,,,,
3. 部分账单记录如充值/提现等交易，不计入为收入或支出类别,,,,,,,,,,
4. 因统计逻辑不同，明细的实付金额累加后可能与统计金额不一致，请以实际交易金额为准,,,,,,,,,,
5. 本明细仅供用户个人对账使用，不具备任何证明效力，禁止用于非法用途,,,,,,,,,,
,,,,,,,,,,
【美团交易账单明细列表】,,,,,,,,,,
交易创建时间,交易成功时间,交易类型,订单标题,收/支,支付方式,订单金额,实付金额,交易单号,商家单号,备注
2026/1/15 10:00,2026/1/15 10:01,充值,Money In,收入,美团钱包,¥100.00,¥100.00,ID001,MID001,/
"""
        path.write_text(content, encoding="utf-8")
        txns = parse_meituan(path)
        assert len(txns) == 1
        assert txns[0].txn_type == "收入"


def test_registry_detects_meituan(meituan_fixture: Path) -> None:
    """测试通过 registry 能正确识别美团账单。"""
    from icostport.sources.registry import resolve_parser
    from icostport.sources.meituan import parse_meituan as expected_parser

    parser = resolve_parser(meituan_fixture)
    assert parser is not None
    assert parser == expected_parser
