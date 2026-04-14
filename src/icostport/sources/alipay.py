"""支付宝记账单解析器。"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from icostport.core.model import Transaction
from icostport.sources.registry import register_detector


def _read_text(path: Path) -> str:
    """尝试多种编码读取支付宝记账单文本。"""
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
    """解析支付宝记账单日期格式。"""
    s = value.strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
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
    """解析支付宝记账单 CSV 文件。"""
    out: list[Transaction] = []
    text = _read_text(path)
    reader = csv.reader(io.StringIO(text))

    header: list[str] | None = None
    header_index = -1
    for index, row in enumerate(reader):
        if not any(cell.strip() for cell in row):
            continue

        normalized = [cell.strip().lower() for cell in row if cell]
        if "记录时间" in normalized and "金额" in normalized and "收支类型" in normalized:
            header = [cell.strip() for cell in row]
            header_index = index
            break

    if header is None:
        return out

    fields = {h.lower(): h for h in header if h}

    def col(name: str) -> str | None:
        return fields.get(name.lower())

    c_date = col("记录时间")
    c_amount = col("金额")
    c_type = col("收支类型")
    c_note = col("备注")
    c_account = col("账户")
    c_source = col("来源")

    if not c_date or not c_amount or not c_type:
        raise ValueError("支付宝记账单缺少必要列（记录时间/金额/收支类型）")

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
        remark = cell_value(c_note)
        account = cell_value(c_account)
        source = cell_value(c_source)
        note_parts = [part for part in (remark, source) if part]
        note = " ".join(note_parts).strip()

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


def detect_alipay_by_content(path: Path) -> bool:
    """通过第二行内容识别支付宝记账单。"""
    try:
        text = _read_text(path)
        lines = text.splitlines()
        return len(lines) >= 2 and "支付宝" in lines[1]
    except OSError:
        return False


register_detector(detect_alipay_by_content, parse_alipay, stage="content")
