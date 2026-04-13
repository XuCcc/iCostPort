"""解析器选择逻辑测试：文件名/内容探测与扩展名兜底优先级。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from icostport.core.exceptions import ParserNotFoundError
from icostport.core.model import Transaction
from icostport.sources import registry


def _mk_tx(path: Path, note: str) -> Transaction:
    return Transaction(
        occurred_at=datetime(2026, 1, 1, 9, 0, 0),
        amount=Decimal("1.00"),
        txn_type="支出",
        note=note,
        source_path=path,
    )


@pytest.fixture
def isolated_registry(monkeypatch):
    """隔离注册中心状态，避免测试间污染。"""
    monkeypatch.setattr(registry, "_REGISTRY", {})
    monkeypatch.setattr(registry, "_FILENAME_DETECTORS", [])
    monkeypatch.setattr(registry, "_CONTENT_DETECTORS", [])


def test_filename_detector_has_higher_priority_than_fallback(tmp_path: Path, isolated_registry) -> None:
    """文件名命中时，应优先于内容探测与扩展名兜底。"""
    path = tmp_path / "special.csv"
    path.write_text("hello", encoding="utf-8")

    def parser_by_name(p: Path) -> list[Transaction]:
        return [_mk_tx(p, "name")]

    def parser_by_content(p: Path) -> list[Transaction]:
        return [_mk_tx(p, "content")]

    def parser_by_ext(p: Path) -> list[Transaction]:
        return [_mk_tx(p, "ext")]

    registry.register_detector(lambda p: p.stem == "special", parser_by_name, stage="filename")
    registry.register_detector(lambda p: True, parser_by_content, stage="content")
    registry.register_parser("csv", parser_by_ext)

    parser = registry.resolve_parser(path)
    assert parser is parser_by_name
    assert registry.parse_path(path)[0].note == "name"


def test_content_detector_matches_without_extension(tmp_path: Path, isolated_registry) -> None:
    """当无后缀时，内容探测命中应可直接选中解析器。"""
    path = tmp_path / "noext_bill"
    path.write_text("magic,header\n1,2\n", encoding="utf-8")

    def parser_by_content(p: Path) -> list[Transaction]:
        return [_mk_tx(p, "content")]

    registry.register_detector(
        lambda p: p.read_text(encoding="utf-8").startswith("magic,header"),
        parser_by_content,
        stage="content",
    )

    parser = registry.resolve_parser(path)
    assert parser is parser_by_content
    assert registry.parse_path(path)[0].note == "content"


def test_resolve_parser_returns_none_when_no_detector_and_no_fallback(
    fixtures_dir: Path,
    isolated_registry,
) -> None:
    """探测与后缀均不命中时，resolve_parser 返回 None。"""
    unknown = fixtures_dir / "unknown_format.txt"
    assert registry.resolve_parser(unknown) is None

    with pytest.raises(ParserNotFoundError):
        registry.parse_path(unknown)
