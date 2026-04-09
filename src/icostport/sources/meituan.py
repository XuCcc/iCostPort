"""美团账单解析器。

美团账单格式：
- 前19行为元数据和说明
- 第20行为表头
- 第21行起为实际数据
"""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from icostport.core.model import Transaction
from icostport.sources.registry import register_detector, register_parser


def _parse_datetime(value: str) -> datetime:
    """解析美团日期格式 YYYY/M/D HH:MM。"""
    s = value.strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_amount(value: str) -> Decimal:
    """解析美团金额格式，去除¥符号。"""
    s = value.strip()
    # 移除¥符号
    if s.startswith("¥"):
        s = s[1:].strip()
    try:
        return Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"金额无效: {value!r}") from e


def parse_meituan(path: Path) -> list[Transaction]:
    """
    解析美团账单 CSV 文件。

    美团账单特殊格式：前19行为元数据/说明，第20行为表头，第21行起为数据。
    表头包括：交易创建时间, 交易成功时间, 交易类型, 订单标题, 收/支,
    支付方式, 订单金额, 实付金额, 交易单号, 商家单号, 备注
    """
    out: list[Transaction] = []

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        # 跳过前19行元数据
        for _ in range(19):
            try:
                next(reader)
            except StopIteration:
                return out

        # 读取第20行表头
        header = next(reader, None)
        if not header:
            return out

        # 规范化列名
        fields = {h.strip().lower(): h for h in header if h}

        def col(name: str) -> str | None:
            return fields.get(name.lower())

        # 定位关键列
        c_date = col("交易成功时间")
        c_amount = col("实付金额")
        c_type = col("收/支")
        c_title = col("订单标题")
        c_account = col("支付方式")
        c_note = col("备注")

        if not c_date or not c_amount or not c_type:
            msg = "美团账单缺少必要列（交易成功时间/实付金额/收/支）"
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

            # 组合备注：订单标题 + 备注
            title = ""
            if c_title:
                title_idx = header.index(c_title)
                title = (row[title_idx] if title_idx < len(row) else "").strip()

            note_field = ""
            if c_note:
                note_idx = header.index(c_note)
                note_field = (row[note_idx] if note_idx < len(row) else "").strip()
                # 美团的"/"表示空备注
                if note_field == "/":
                    note_field = ""

            note = f"{title} {note_field}".strip()

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


def detect_meituan_by_name(path: Path) -> bool:
    """通过文件名关键字识别美团账单。"""
    stem = path.stem.lower()
    return "美团" in stem


def detect_meituan_by_content(path: Path) -> bool:
    """通过第一行内容识别美团账单。"""
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            first_line = f.readline().strip()
            return "美团" in first_line
    except OSError:
        return False


register_detector(detect_meituan_by_name, parse_meituan, stage="filename")
register_detector(detect_meituan_by_content, parse_meituan, stage="content")
