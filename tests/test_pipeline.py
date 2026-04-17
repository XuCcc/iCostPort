"""pipeline 解析阶段行为测试。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from icostport.core.model import Transaction
from icostport.pipeline import run


def test_run_skips_unrecognized_files_and_continues_pipeline(
    monkeypatch,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    """多输入混合场景下，未识别文件应 warning+skip，且仍写出结果。"""
    recognized = fixtures_dir / "sample_bank_a.csv"
    unknown = fixtures_dir / "unknown_format.txt"
    output = tmp_path / "result.xlsx"
    config = fixtures_dir / "config_minimal.yml"

    warnings: list[str] = []

    def parser_for_recognized(path: Path) -> list[Transaction]:
        return [
            Transaction(
                occurred_at=datetime(2026, 1, 1, 8, 0, 0),
                amount=Decimal("20.50"),
                txn_type="支出",
                note="麦当劳早餐",
                source_path=path,
            )
        ]

    def fake_resolve_parser(path: Path):
        if path == recognized:
            return parser_for_recognized
        return None

    monkeypatch.setattr("icostport.pipeline.resolve_parser", fake_resolve_parser)
    monkeypatch.setattr("icostport.pipeline.logger.warning", lambda msg, *a: warnings.append(msg.format(*a)))

    run([recognized, unknown], output, config, verbose=False)

    assert output.exists()
    assert any("跳过未识别文件" in w for w in warnings)
    assert any("共跳过 1 个未识别文件" in w for w in warnings)


def test_run_respects_account_parse_and_only_expense_flags(
    monkeypatch,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    """account_parse=False 清空账户，only_expense=True 仅保留支出。"""
    sample_file = fixtures_dir / "sample_bank_a.csv"
    output_file = tmp_path / "out.xlsx"
    config = fixtures_dir / "config_minimal.yml"

    written_rows: list = []

    def fake_write_icost_workbook(path: Path, rows: list):
        written_rows.extend(rows)

    def fake_resolve_parser(path: Path):
        def parser(_: Path) -> list[Transaction]:
            return [
                Transaction(
                    occurred_at=datetime(2026, 1, 1, 8, 0, 0),
                    amount=Decimal("20.50"),
                    txn_type="支出",
                    note="早餐",
                    account1="招商银行",
                    account2="微信支付",
                    source_path=path,
                ),
                Transaction(
                    occurred_at=datetime(2026, 1, 2, 9, 0, 0),
                    amount=Decimal("30.00"),
                    txn_type="收入",
                    note="退款",
                    account1="支付宝",
                    account2="余额",
                    source_path=path,
                ),
            ]
        return parser

    monkeypatch.setattr("icostport.pipeline.resolve_parser", fake_resolve_parser)
    monkeypatch.setattr("icostport.pipeline.write_icost_workbook", fake_write_icost_workbook)

    run([sample_file], output_file, config, verbose=False, account_parse=False, only_expense=True)

    assert len(written_rows) == 1
    row = written_rows[0]
    assert row.txn_type == "支出"
    assert row.account1 == ""
    assert row.account2 == ""
