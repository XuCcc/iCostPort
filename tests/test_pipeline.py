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
