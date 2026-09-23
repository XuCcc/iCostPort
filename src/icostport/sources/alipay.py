"""支付宝交易明细解析器。

支付宝交易明细格式：
- 开头若干行为元数据/导出信息与特别提示
- 中间某一行为表头（交易时间/交易分类/交易对方/.../收/支/金额/...）
- 表头之后为实际交易数据
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from icostport.core.model import Transaction
from icostport.sources.registry import register_detector


def _read_text(path: Path) -> str:
    """尝试多种编码读取支付宝交易明细文本。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        if "�" in text:
            continue
        return text
    return path.read_text(encoding="gb18030", errors="replace")


def _parse_datetime(value: str) -> datetime:
    """解析支付宝日期格式，如 2026/6/29 15:57。"""
    s = value.strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_amount(value: str) -> Decimal:
    """解析支付宝金额字符串。"""
    s = value.strip().replace("¥", "").replace("￥", "").replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"金额无效: {value!r}") from exc


def parse_alipay(path: Path) -> list[Transaction]:
    """解析支付宝交易明细 CSV 文件。

    表头包括：交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,
    收/付款方式,交易状态,交易订单号,商家订单号,备注
    """
    out: list[Transaction] = []
    text = _read_text(path)
    reader = csv.reader(io.StringIO(text))

    # 扫描定位表头行（含 交易时间/金额/收/支）
    header: list[str] | None = None
    header_index = -1
    for index, row in enumerate(reader):
        if not any(cell.strip() for cell in row):
            continue
        normalized = [cell.strip() for cell in row if cell.strip()]
        if "交易时间" in normalized and "收/支" in normalized:
            header = [cell.strip() for cell in row]
            header_index = index
            break

    if header is None:
        return out

    fields = {h.lower(): h for h in header if h}

    def col(name: str) -> str | None:
        return fields.get(name.lower())

    c_date = col("交易时间")
    c_amount = col("金额")
    c_type = col("收/支")
    c_category = col("交易分类")
    c_counterparty = col("交易对方")
    c_goods = col("商品说明")
    c_method = col("收/付款方式")
    c_note = col("备注")

    if not c_date or not c_amount or not c_type:
        raise ValueError("支付宝交易明细缺少必要列（交易时间/金额/收/支）")

    # 重新读取，跳过表头及之前的行，逐行解析
    reader = csv.reader(io.StringIO(text))
    for row_index, row in enumerate(reader):
        if row_index <= header_index:
            continue
        if not any(cell.strip() for cell in row):
            continue

        def cell_value(col_name: str | None) -> str:
            if col_name is None:
                return ""
            try:
                idx = header.index(col_name)
            except ValueError:
                return ""
            return (row[idx] if idx < len(row) else "").strip()

        raw_date = cell_value(c_date)
        raw_amount = cell_value(c_amount)
        raw_type = cell_value(c_type)

        if not raw_date or not raw_amount or not raw_type:
            continue

        try:
            amount = _parse_amount(raw_amount)
        except ValueError:
            continue

        txn_type = "支出" if "支出" in raw_type else "收入" if "收入" in raw_type else "中性"

        # 组合备注：交易对方 + 商品说明 + 备注
        counterparty = cell_value(c_counterparty)
        goods = cell_value(c_goods)
        remark = cell_value(c_note)
        note_parts = [part for part in (counterparty, goods, remark) if part]
        note = " ".join(note_parts).strip()

        # 账户使用收/付款方式
        account = cell_value(c_method)

        tx = Transaction(
            occurred_at=_parse_datetime(raw_date),
            amount=amount,
            txn_type=txn_type,
            note=note,
            account1=account,
            account2="",
            currency="CNY",
            source_path=path,
        )
        out.append(tx)

    return out


def detect_alipay_by_name(path: Path) -> bool:
    """通过文件名关键字识别支付宝交易明细。"""
    return "支付宝" in path.stem


def detect_alipay_by_content(path: Path) -> bool:
    """通过开头元数据内容识别支付宝交易明细。"""
    try:
        text = _read_text(path)
        lines = text.splitlines()
        return any("支付宝" in line for line in lines[:10])
    except OSError:
        return False


register_detector(detect_alipay_by_name, parse_alipay, stage="filename")
register_detector(detect_alipay_by_content, parse_alipay, stage="content")
