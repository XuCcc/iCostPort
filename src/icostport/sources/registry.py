"""注册并选择解析器：文件名探测 -> 内容探测 -> 扩展名兜底。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal

from icostport.core.exceptions import ParserNotFoundError
from icostport.core.model import Transaction

ParserFn = Callable[[Path], list[Transaction]]
DetectorFn = Callable[[Path], bool]
DetectorStage = Literal["filename", "content"]

_REGISTRY: dict[str, ParserFn] = {}
_FILENAME_DETECTORS: list[tuple[DetectorFn, ParserFn]] = []
_CONTENT_DETECTORS: list[tuple[DetectorFn, ParserFn]] = []


def register_parser(ext: str, fn: ParserFn) -> None:
    """注册扩展名（不含点，小写），例如 ``csv``。"""
    key = ext.lower().lstrip(".")
    _REGISTRY[key] = fn


def register_detector(
    detector: DetectorFn,
    parser: ParserFn,
    *,
    stage: DetectorStage = "content",
) -> None:
    """注册探测器，``stage`` 支持 ``filename`` 或 ``content``。"""
    if stage == "filename":
        _FILENAME_DETECTORS.append((detector, parser))
        return
    _CONTENT_DETECTORS.append((detector, parser))


def resolve_parser(path: Path) -> ParserFn | None:
    """两段式选择解析器：文件名优先、再看内容、最后扩展名兜底。"""
    for detector, parser in _FILENAME_DETECTORS:
        if _safe_detect(detector, path):
            return parser

    for detector, parser in _CONTENT_DETECTORS:
        if _safe_detect(detector, path):
            return parser

    ext = path.suffix.lower().lstrip(".")
    if ext and ext in _REGISTRY:
        return _REGISTRY[ext]
    return None


def parse_path(path: Path) -> list[Transaction]:
    """根据探测+兜底策略选择解析器并解析。"""
    parser = resolve_parser(path)
    if parser is None:
        ext = path.suffix.lower().lstrip(".")
        raise ParserNotFoundError(f"未找到可用解析器（扩展名 {ext!r}）: {path}")
    return parser(path)


def _safe_detect(detector: DetectorFn, path: Path) -> bool:
    """探测阶段异常视为未命中，避免影响后续兜底。"""
    try:
        return bool(detector(path))
    except OSError:
        return False
