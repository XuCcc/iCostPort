"""拼多多账单解析器。"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from icostport.core.model import Transaction
from icostport.sources.registry import register_detector


def _read_text(path: Path) -> str:
    """尝试多种编码读取拼多多账单文本。"""
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
    """解析拼多多账单日期格式。"""
    s = value.strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_amount(value: str) -> Decimal:
    """解析拼多多金额字符串。"""
    s = value.strip().replace("¥", "").replace("￥", "").replace(",", "")
    if not s:
        raise ValueError("金额为空")
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"金额无效: {value!r}") from exc


def parse_pdd(path: Path) -> list[Transaction]:
    """解析拼多多 CSV 账单文件。"""
    out: list[Transaction] = []
    text = _read_text(path)
    reader = csv.reader(io.StringIO(text))

    header: list[str] | None = None
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        header = [cell.strip() for cell in row]
        break

    if not header:
        return out

    fields = {h.lower(): h for h in header if h}

    def col(name: str) -> str | None:
        return fields.get(name.lower())

    c_date = col("时间")
    c_amount = col("实付")
    c_shop = col("店铺")
    c_product = col("商品")
    c_spec = col("规格")
    c_pay_method = col("支付方式")
    c_status = col("状态")

    if not c_date or not c_amount:
        raise ValueError("拼多多账单缺少必要列（时间/实付）")

    # 重新读取数据行
    reader = csv.reader(io.StringIO(text))
    header_index = 0
    for row_index, row in enumerate(reader):
        if row_index <= header_index:
            continue
        if not any(cell.strip() for cell in row):
            continue

        def get_cell(name: str | None) -> str:
            if name is None:
                return ""
            try:
                idx = header.index(name)
            except ValueError:
                return ""
            return (row[idx] if idx < len(row) else "").strip()

        raw_date = get_cell(c_date)
        raw_amount = get_cell(c_amount)
        raw_shop = get_cell(c_shop)
        raw_product = get_cell(c_product)
        raw_spec = get_cell(c_spec)
        raw_method = get_cell(c_pay_method)
        raw_status = get_cell(c_status)

        if not raw_date or not raw_amount:
            continue

        try:
            amount = _parse_amount(raw_amount)
        except ValueError:
            continue

        if raw_status and ("退款" in raw_status or "退货" in raw_status):
            txn_type = "收入"
        else:
            txn_type = "支出" if amount >= 0 else "收入"

        note_parts = [part for part in (raw_shop, raw_product, raw_spec, raw_status) if part and part != "/"]
        note = " ".join(note_parts).strip()

        out.append(
            Transaction(
                occurred_at=_parse_datetime(raw_date),
                amount=amount,
                txn_type=txn_type,
                note=note,
                account1=raw_method,
                account2="",
                currency="CNY",
                source_path=path,
            )
        )

    return out


def detect_pdd_by_name(path: Path) -> bool:
    """通过文件名关键字识别拼多多账单。"""
    stem = path.stem.lower()
    return "pdd" in stem or "拼多多" in stem


def detect_pdd_by_content(path: Path) -> bool:
    """通过表头内容识别拼多多账单。"""
    try:
        text = _read_text(path)
        first_line = text.splitlines()[0] if text else ""
        normalized = [cell.strip() for cell in first_line.split(",")]
        return all(key in normalized for key in ("订单号", "时间", "店铺", "实付"))
    except OSError:
        return False


register_detector(detect_pdd_by_name, parse_pdd, stage="filename")
register_detector(detect_pdd_by_content, parse_pdd, stage="content")
