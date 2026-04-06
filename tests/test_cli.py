"""CLI 行为测试。"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from icostport import cli as cli_module


def test_convert_command_invokes_pipeline_with_expected_args(
    monkeypatch,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    """convert 子命令应将参数原样编排后传入 pipeline.run。"""
    sample_file = fixtures_dir / "sample_bank_a.csv"
    config_file = fixtures_dir / "config_minimal.yml"
    output_file = tmp_path / "out.xlsx"

    captured: dict[str, object] = {}

    def fake_run(
        input_paths: list[Path],
        output: Path,
        config: Path | None,
        *,
        verbose: bool = False,
    ) -> None:
        captured["input_paths"] = input_paths
        captured["output"] = output
        captured["config"] = config
        captured["verbose"] = verbose

    monkeypatch.setattr("icostport.pipeline.run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "-v",
            "convert",
            str(sample_file),
            "--config",
            str(config_file),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["input_paths"] == [sample_file]
    assert captured["output"] == output_file
    assert captured["config"] == config_file
    assert captured["verbose"] is True


def test_convert_command_accepts_multiple_input_paths(
    monkeypatch,
    fixtures_dir: Path,
    tmp_path: Path,
) -> None:
    """convert 子命令应支持多输入路径。"""
    input_a = fixtures_dir / "sample_bank_a.csv"
    input_b = tmp_path / "sample_b.csv"
    input_b.write_text(
        "date,amount,type\n2026-01-02 09:00:00,66.00,支出\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "out.xlsx"

    captured: dict[str, object] = {}

    def fake_run(
        input_paths: list[Path],
        output: Path,
        config: Path | None,
        *,
        verbose: bool = False,
    ) -> None:
        captured["input_paths"] = input_paths
        captured["output"] = output
        captured["config"] = config
        captured["verbose"] = verbose

    monkeypatch.setattr("icostport.pipeline.run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "convert",
            str(input_a),
            str(input_b),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["input_paths"] == [input_a, input_b]
    assert captured["output"] == output_file
    assert captured["config"] is None
    assert captured["verbose"] is False
