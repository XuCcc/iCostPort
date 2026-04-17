"""使用 csv 写出 .csv：首行为表头，数据自第 2 行起。"""

from __future__ import annotations

import csv
from pathlib import Path

from icostport.icost.schema import ICOST_HEADERS, ICostRow


def write_icost_workbook(path: Path, rows: list[ICostRow]) -> None:
    """写入 ICost 模板兼容 CSV 文件（首行表头与 :data:`ICOST_HEADERS` 一致）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(ICOST_HEADERS)
        for row in rows:
            values = (
                row.date_display,
                row.txn_type,
                float(row.amount),
                row.primary,
                row.secondary,
                row.account1,
                row.account2,
                row.note,
                row.currency,
                row.tags,
            )
            writer.writerow(values)
