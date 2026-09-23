"""编排：解析 → 合并 → 处理 → 归类 → 写出 ICost。"""

from __future__ import annotations

from decimal import Decimal
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
from icostport.sources.registry import resolve_parser

# 确保内置解析器完成注册
import icostport.sources  # noqa: F401


def _log_bill_summary(path: Path, txs: list[Transaction]) -> None:
    """打印已识别账单的基本信息：笔数、时间范围、收支金额合计。"""
    if not txs:
        logger.info("  └ {}：解析出 0 条记录", path.name)
        return

    times = [t.occurred_at for t in txs]
    start, end = min(times), max(times)
    expense = sum((t.amount for t in txs if t.txn_type == "支出"), Decimal(0))
    income = sum((t.amount for t in txs if t.txn_type == "收入"), Decimal(0))
    logger.info(
        "  └ {}：{} 条记录，时间 {} ~ {}，支出 {} 元 / 收入 {} 元",
        path.name,
        len(txs),
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        expense,
        income,
    )


def run(
    input_paths: list[Path],
    output: Path,
    config: Path | None,
    *,
    verbose: bool = False,
    account_parse: bool = False,
    only_expense: bool = True,
) -> None:
    """
    端到端执行：多文件解析、合并、去重、过滤、排序、规则/AI 归类、写出 xlsx。
    """
    configure_logging(verbose=verbose)
    settings = load_settings(config)

    partitions: list[list[Transaction]] = []
    skipped = 0
    for p in input_paths:
        parser = resolve_parser(p)
        if parser is None:
            skipped += 1
            logger.warning("跳过未识别文件: {}（可在 sources 中新增探测器或扩展名注册）", p)
            continue

        logger.info("识别账单: {}（解析器 {}）", p.name, parser.__name__)
        parsed = parser(p)
        _log_bill_summary(p, parsed)
        partitions.append(parsed)

    if skipped:
        logger.warning("共跳过 {} 个未识别文件，继续处理其余输入。", skipped)

    txs = merge_lists(partitions)

    if not account_parse:
        for tx in txs:
            tx.account1 = ""
            tx.account2 = ""

    dedupe_cfg = settings.processing.dedupe
    if dedupe_cfg.enabled:
        on_dup = dedupe_cfg.on_duplicate
        txs = dedupe_transactions(txs, on_duplicate=on_dup)

    filt = settings.processing.filter or {}
    txs = apply_filters(txs, filt)

    if only_expense:
        txs = [tx for tx in txs if tx.txn_type == "支出"]

    txs = sort_by_time(txs)

    total_txs = len(txs)
    rules_assigned = apply_keyword_rules(txs, settings)
    ai_assigned = run_ai_categorize(txs, settings, verbose=verbose)
    logger.info(
        "分类统计：共 {} 条账单，{} 条由 rules 分类，{} 条由 AI 分类。",
        total_txs,
        rules_assigned,
        ai_assigned,
    )

    rows = [transaction_to_icost_row(t) for t in txs]
    write_icost_workbook(output, rows)
    logger.info("已写出 ICost 文件: {}", output)
