"""可选：对仍未归类项调用 LLM；结果须经与 rules 相同的白名单校验。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from icostport.core.model import Transaction

if TYPE_CHECKING:
    from icostport.core.settings import Settings


def run_ai_categorize(transactions: list[Transaction], settings: Settings) -> None:
    """
    若 ``settings.ai.enabled`` 为真，则对「一级/二级仍为空的交易」尝试 AI 归类。
    当前为骨架：仅记录日志，不接 API；后续在 :mod:`icostport.ai.client` 中接入。
    """
    ai_cfg = settings.ai
    if not ai_cfg.enabled:
        return

    pending = [tx for tx in transactions if tx.primary_category is None]

    if not pending:
        return

    max_items = ai_cfg.max_items
    if max_items > 0:
        pending = pending[:max_items]

    logger.info("AI 归类骨架：待处理 {} 条（尚未调用模型）", len(pending))
    # 占位：此处调用 AIClient.chat_completion，解析结果后用 categorize.rules.is_allowed_pair 校验
