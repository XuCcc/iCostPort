"""京东账单解析器。

京东账单格式：
- 前17行为元数据和说明
- 第18行为表头
- 第19行起为实际数据
"""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from icostport.core.model import Transaction
from icostport.sources.registry import register_detector, register_parser


def _parse_datetime(value: str) -> datetime:
    """解析京东日期格式 YYYY-MM-DD HH:MM:SS。"""
    s = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_amount(value: str) -> Decimal:
    """解析京东金额格式。"""
    s = value.strip()
    try:
        return Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"金额无效: {value!r}") from e


def parse_jd(path: Path) -> list[Transaction]:
    """
    解析京东账单 CSV 文件。

    京东账单特殊格式：前21行为元数据/说明，第22行为表头，第23行起为数据。
    表头包括：交易时间,商户名称,交易说明,金额,收/付款方式,交易状态,收/支,交易分类,交易订单号,商家订单号,备注
    """
    out: list[Transaction] = []

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        # 跳过前21行元数据
        for _ in range(21):
            try:
                next(reader)
            except StopIteration:
                return out

        # 读取第22行表头
        header = next(reader, None)
        if not header:
            return out

        # 规范化列名
        fields = {h.strip().lower(): h for h in header if h}

        def col(name: str) -> str | None:
            return fields.get(name.lower())

        # 定位关键列
        c_date = col("交易时间")
        c_amount = col("金额")
        c_type = col("收/支")
        c_merchant = col("商户名称")
        c_description = col("交易说明")
        c_note = col("备注")

        if not c_date or not c_amount or not c_type:
            msg = "京东账单缺少必要列（交易时间/金额/收/支）"
            raise ValueError(msg)

        # 解析数据行
        for row in reader:
            # 跳过空行
            if not any(cell.strip() for cell in row):
                continue

            date_idx = header.index(c_date)
            raw_date = (row[date_idx] if date_idx < len(row) else "").strip()
            if not raw_date:
                continue

            amount_idx = header.index(c_amount)
            raw_amt = (row[amount_idx] if amount_idx < len(row) else "").strip()
            if not raw_amt:
                continue

            type_idx = header.index(c_type)
            raw_type = (row[type_idx] if type_idx < len(row) else "").strip()

            # 解析交易类型：支出/收入
            txn_type = "支出" if "支出" in raw_type else "收入"

            # 组合备注：商户名称 + 交易说明 + 备注
            merchant = ""
            if c_merchant:
                merchant_idx = header.index(c_merchant)
                merchant = (row[merchant_idx] if merchant_idx < len(row) else "").strip()

            description = ""
            if c_description:
                desc_idx = header.index(c_description)
                description = (row[desc_idx] if desc_idx < len(row) else "").strip()

            note_field = ""
            if c_note:
                note_idx = header.index(c_note)
                note_field = (row[note_idx] if note_idx < len(row) else "").strip()

            note = f"{merchant} {description} {note_field}".strip()

            tx = Transaction(
                occurred_at=_parse_datetime(raw_date),
                amount=_parse_amount(raw_amt),
                txn_type=txn_type,
                note=note,
                account1="",
                account2="",
                currency="CNY",
                source_path=path,
            )
            out.append(tx)

    return out


def detect_jd_by_name(path: Path) -> bool:
    """通过文件名关键字识别京东账单。"""
    stem = path.stem.lower()
    return "京东" in stem


def detect_jd_by_content(path: Path) -> bool:
    """通过第二行内容识别京东账单。"""
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            # 跳过第一行
            f.readline()
            # 检查第二行
            second_line = f.readline().strip()
            return "京东" in second_line
    except OSError:
        return False


register_detector(detect_jd_by_name, parse_jd, stage="filename")
register_detector(detect_jd_by_content, parse_jd, stage="content")