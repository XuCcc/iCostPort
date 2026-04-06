"""编排：解析 → 合并 → 处理 → 归类 → 写出 ICost。"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from icostport.categorize.ai_categorize import run_ai_categorize
from icostport.categorize.rules import apply_keyword_rules
from icostport.core.logging_ import configure_logging
from icostport.core.model import Transaction
from icostport.core.settings import load_settings
from icostport.icost.schema import transaction_to_icost_row
from icostport.icost.writer import write_icost_workbook
from icostport.processing.dedupe import dedupe_transactions
from icostport.processing.filter import apply_filters
from icostport.processing.merge import merge_lists
from icostport.processing.organize import sort_by_time
from icostport.sources.registry import parse_path

# 确保内置解析器完成注册
import icostport.sources.example_csv  # noqa: F401


def run(
    input_paths: list[Path],
    output: Path,
    config: Path | None,
    *,
    verbose: bool = False,
) -> None:
    """
    端到端执行：多文件解析、合并、去重、过滤、排序、规则/AI 归类、写出 xlsx。
    """
    configure_logging(verbose=verbose)
    settings = load_settings(config)

    partitions: list[list[Transaction]] = []
    for p in input_paths:
        logger.info("解析: {}", p)
        partitions.append(parse_path(p))

    txs = merge_lists(partitions)

    dedupe_cfg = settings.processing.dedupe
    if dedupe_cfg.enabled:
        on_dup = dedupe_cfg.on_duplicate
        txs = dedupe_transactions(txs, on_duplicate=on_dup)

    filt = settings.processing.filter or {}
    txs = apply_filters(txs, filt)

    txs = sort_by_time(txs)

    apply_keyword_rules(txs, settings)
    run_ai_categorize(txs, settings)

    rows = [transaction_to_icost_row(t) for t in txs]
    write_icost_workbook(output, rows)
    logger.info("已写出 ICost 文件: {}", output)
