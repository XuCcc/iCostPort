"""京东账单解析器测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from icostport.sources.jd import (
    detect_jd_by_content,
    detect_jd_by_name,
    parse_jd,
)


@pytest.fixture
def jd_fixture(tmp_path: Path) -> Path:
    """创建京东账单测试 fixture。"""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "京东账单_sample.csv"
    return fixture_path


class TestJdDetection:
    """京东账单检测测试。"""

    def test_detect_by_filename(self, jd_fixture: Path) -> None:
        """通过文件名包含"京东"识别。"""
        assert detect_jd_by_name(jd_fixture)

    def test_detect_by_content(self, jd_fixture: Path) -> None:
        """通过内容（第二行包含"京东"）识别。"""
        assert detect_jd_by_content(jd_fixture)

    def test_not_detected_by_unrelated_filename(self, tmp_path: Path) -> None:
        """不匹配无关文件名。"""
        path = tmp_path / "other_bank.csv"
        path.write_text("any content")
        assert not detect_jd_by_name(path)


class TestJdParsing:
    """京东账单解析测试。"""

    def test_parse_basic(self, jd_fixture: Path) -> None:
        """基本解析：行数与字段正确。"""
        txns = parse_jd(jd_fixture)
        assert len(txns) == 2

    def test_parse_fields(self, jd_fixture: Path) -> None:
        """解析字段正确性。"""
        txns = parse_jd(jd_fixture)

        # 第一条交易
        assert txns[0].occurred_at == datetime(2026, 3, 22, 10, 55, 40)
        assert txns[0].amount == Decimal("11.81")
        assert txns[0].txn_type == "支出"
        assert "京东外卖 测试商品1 等多件 测试备注1" in txns[0].note
        assert txns[0].currency == "CNY"

        # 第二条交易
        assert txns[1].occurred_at == datetime(2026, 3, 20, 15, 30, 22)
        assert txns[1].amount == Decimal("18.88")
        assert txns[1].txn_type == "支出"
        assert "京东商城 测试商品2" in txns[1].note

    def test_parse_amount_decimal(self, tmp_path: Path) -> None:
        """测试小数金额解析。"""
        path = tmp_path / "test_jd.csv"
        content = """导出信息：
京东账号名：TestUser
申请时间：2026-04-13 11:02:13
日期区间：2026-03-01 至 2026-03-31
导出交易类型：全部
导出交易场景：全部
共：1笔记录
收入：0笔，0.00元
支出：1笔，99.99元
不计收支：0笔，0.00元

特别提示
1.本明细为每笔订单支付的明细，不包括已删除的记录；如需计算白条相关费用明细，请访问"白条-查账还款"进行查看；
2.个人资金互转、全额退款等记为【不计收支】类，部分退款的支出金额为剔除退款后的支付金额；
3.因系统原因或通讯故障等偶发因素导致本明细与实际交易结果不符时，以实际交易情况为准；
4.因统计逻辑不同，明细金额直接累加后，可能会和上方统计金额不一致，请以实际交易金额为准；
5.京东快捷支付等非余额支付方式可能既产生京东交易也同步产生银行交易，因此请勿使用本回单进行重复记账；
6.明细如经任何涂改、编造，均立即失去效力；
7.禁止将本回单用于非法用途；
8.本明细仅供个人对账使用。

交易时间,商户名称,交易说明,金额,收/付款方式,交易状态,收/支,交易分类,交易订单号,商家订单号,备注
2026-03-15 10:00:00,测试商户,测试商品,99.99,微信支付,交易成功,支出,食品酒饮 其他网购,34452XXXXXXXXX6728,19XXXXXXXXXXX165476508,测试备注
"""
        path.write_text(content, encoding="utf-8")
        txns = parse_jd(path)
        assert len(txns) == 1
        assert txns[0].amount == Decimal("99.99")

    def test_parse_skip_empty_rows(self, tmp_path: Path) -> None:
        """跳过空行。"""
        path = tmp_path / "test_jd_empty.csv"
        content = """导出信息：
京东账号名：TestUser
申请时间：2026-04-13 11:02:13
日期区间：2026-03-01 至 2026-03-31
导出交易类型：全部
导出交易场景：全部
共：1笔记录
收入：0笔，0.00元
支出：1笔，11.81元
不计收支：0笔，0.00元

特别提示
1.本明细为每笔订单支付的明细，不包括已删除的记录；如需计算白条相关费用明细，请访问"白条-查账还款"进行查看；
2.个人资金互转、全额退款等记为【不计收支】类，部分退款的支出金额为剔除退款后的支付金额；
3.因系统原因或通讯故障等偶发因素导致本明细与实际交易结果不符时，以实际交易情况为准；
4.因统计逻辑不同，明细金额直接累加后，可能会和上方统计金额不一致，请以实际交易金额为准；
5.京东快捷支付等非余额支付方式可能既产生京东交易也同步产生银行交易，因此请勿使用本回单进行重复记账；
6.明细如经任何涂改、编造，均立即失去效力；
7.禁止将本回单用于非法用途；
8.本明细仅供个人对账使用。

交易时间,商户名称,交易说明,金额,收/付款方式,交易状态,收/支,交易分类,交易订单号,商家订单号,备注
2026-03-22 10:55:40,京东外卖,测试商品,11.81,苹果支付,交易成功,支出,食品酒饮 其他网购,34452XXXXXXXXX6726,19XXXXXXXXXXX165476506,测试备注
,,,,,,,,,,
"""
        path.write_text(content, encoding="utf-8")
        txns = parse_jd(path)
        assert len(txns) == 1

    def test_parse_missing_required_columns(self, tmp_path: Path) -> None:
        """缺少必要列时抛出异常。"""
        path = tmp_path / "test_jd_invalid.csv"
        content = """导出信息：
京东账号名：TestUser
申请时间：2026-04-13 11:02:13
日期区间：2026-03-01 至 2026-03-31
导出交易类型：全部
导出交易场景：全部
共：1笔记录
收入：0笔，0.00元
支出：1笔，11.81元
不计收支：0笔，0.00元

特别提示
1.本明细为每笔订单支付的明细，不包括已删除的记录；如需计算白条相关费用明细，请访问"白条-查账还款"进行查看；
2.个人资金互转、全额退款等记为【不计收支】类，部分退款的支出金额为剔除退款后的支付金额；
3.因系统原因或通讯故障等偶发因素导致本明细与实际交易结果不符时，以实际交易情况为准；
4.因统计逻辑不同，明细金额直接累加后，可能会和上方统计金额不一致，请以实际交易金额为准；
5.京东快捷支付等非余额支付方式可能既产生京东交易也同步产生银行交易，因此请勿使用本回单进行重复记账；
6.明细如经任何涂改、编造，均立即失去效力；
7.禁止将本回单用于非法用途；
8.本明细仅供个人对账使用。

商户名称,交易说明,金额,收/付款方式,交易状态,交易分类,交易订单号,商家订单号,备注
京东外卖,测试商品,11.81,苹果支付,交易成功,支出,食品酒饮 其他网购,34452XXXXXXXXX6726,19XXXXXXXXXXX165476506,测试备注
"""
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match="缺少必要列"):
            parse_jd(path)