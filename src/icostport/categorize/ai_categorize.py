"""可选：对仍未归类项调用 LLM；结果须经与 rules 相同的白名单校验。"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from icostport.ai.client import AIClient
from icostport.categorize.rules import build_category_pairs, is_allowed_pair
from icostport.core.model import Transaction

if TYPE_CHECKING:
    from icostport.core.settings import Settings


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        return "\n".join(text.splitlines()[1:-1]).strip()
    return text


_PROMPT_FILE = Path(__file__).resolve().parents[1] / "ai" / "prompt.md"


def _load_prompt_template() -> dict[str, str]:
    raw = _PROMPT_FILE.read_text(encoding="utf-8")
    system_match = re.search(r"^##\s*system\s*$\n(.*?)(?=^##\s*user\s*$|\Z)", raw, flags=re.MULTILINE | re.DOTALL)
    user_match = re.search(r"^##\s*user\s*$\n(.*?)(?=^##\s*|\Z)", raw, flags=re.MULTILINE | re.DOTALL)
    if not system_match or not user_match:
        raise ValueError(f"AI prompt 模板格式错误: {_PROMPT_FILE}")
    return {
        "system": system_match.group(1).strip(),
        "user": user_match.group(1).strip(),
    }


def _parse_ai_response(text: str) -> list[tuple[int, str, str]]:
    text = _strip_code_fence(text)
    if not text:
        return []

    def _normalize_item(item: dict) -> tuple[int, str, str] | None:
        if not isinstance(item, dict):
            return None
        idx = item.get("index")
        if not isinstance(idx, int):
            return None

        primary = item.get("primary")
        secondary = item.get("secondary")
        if primary is None or primary == "null":
            primary = None
        if secondary is None or secondary == "null":
            secondary = None
        if primary is None or secondary is None:
            return None

        return (idx, str(primary).strip(), str(secondary).strip())

    parsed = None
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(text)
            break
        except Exception:
            continue

    if not isinstance(parsed, list):
        return []

    results: list[tuple[int, str, str]] = []
    for item in parsed:
        normalized = _normalize_item(item)
        if normalized is not None:
            results.append(normalized)
    return results


def _build_prompt(transactions: list[Transaction], settings: Settings) -> list[dict[str, str]]:
    categories_text = []
    for primary, secondaries in settings.categories.items():
        categories_text.append(f"- {primary}: {', '.join(secondaries)}")

    examples = []
    for idx, tx in enumerate(transactions):
        examples.append(
            f"{idx}. 金额：{tx.amount}；类型：{tx.txn_type}；备注：{tx.note}"
        )

    if categories_text:
        taxonomy = "可用分类:\n" + "\n".join(categories_text)
    else:
        taxonomy = "当前未配置 categories 白名单，可输出任意合理的一级/二级分类。"

    template = _load_prompt_template()
    user_prompt = template["user"].format(
        taxonomy=taxonomy,
        transactions="\n".join(examples),
    )

    return [
        {
            "role": "system",
            "content": template["system"],
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def run_ai_categorize(transactions: list[Transaction], settings: Settings, *, verbose: bool = False) -> int:
    """
    若 ``settings.ai.enabled`` 为真，则对「一级/二级仍为空的交易」尝试 AI 归类。
    仅在 AI 返回结果后填充未分类交易，结果须经白名单校验。
    返回实际由 AI 分类成功的交易数量。
    """
    ai_cfg = settings.ai
    if not ai_cfg.enabled:
        return 0

    candidates = transactions if not ai_cfg.only_if_uncategorized else [tx for tx in transactions if tx.primary_category is None]
    if not candidates:
        return 0

    max_items = ai_cfg.max_items
    total_candidates = len(candidates)
    logger.info(
        "AI 归类：待处理 {} 条交易，max_items={}，only_if_uncategorized={}",
        total_candidates,
        max_items,
        ai_cfg.only_if_uncategorized,
    )

    client = AIClient(ai_cfg.model_dump())
    allowed_pairs = build_category_pairs(settings.categories)
    categories_nonempty = bool(settings.categories)

    assigned = 0
    ignored = 0
    batch_no = 0

    while candidates:
        batch_no += 1
        batch = candidates if max_items <= 0 else candidates[:max_items]
        logger.info("AI 归类批次 {}：处理 {} 条交易", batch_no, len(batch))

        messages = _build_prompt(batch, settings)
        response = client.chat_completion(messages, timeout=ai_cfg.timeout)
        if not response:
            logger.warning("AI 归类第 {} 批次未返回结果，已终止", batch_no)
            break

        parsed = _parse_ai_response(response)
        if not parsed:
            logger.warning("AI 归类第 {} 批次返回内容无法解析，已终止。响应: {}", batch_no, response)
            break

        batch_assigned = 0
        for idx, primary, secondary in parsed:
            if idx < 0 or idx >= len(batch):
                logger.warning("AI 返回的 index 超出范围，已忽略: {}", idx)
                ignored += 1
                continue

            tx = batch[idx]
            if tx.primary_category is not None:
                continue

            if not is_allowed_pair(primary, secondary, allowed_pairs, categories_nonempty):
                logger.warning(
                    "AI 分类结果不在白名单内，已忽略: primary={!r} secondary={!r}",
                    primary,
                    secondary,
                )
                ignored += 1
                continue

            tx.primary_category = primary
            tx.secondary_category = secondary
            assigned += 1
            batch_assigned += 1

            if verbose:
                logger.debug(
                    "AI 分类交易 {}: 备注={!r} -> primary={!r} secondary={!r}",
                    idx,
                    tx.note,
                    primary,
                    secondary,
                )

        if not batch_assigned and max_items > 0:
            logger.warning("AI 归类第 {} 批次未分配任何新分类，已终止后续批次。", batch_no)
            break

        candidates = [tx for tx in candidates if tx.primary_category is None]

        if max_items <= 0:
            break

    logger.info("AI 归类完成：{} 条已分配，{} 条结果被忽略。", assigned, ignored)
    return assigned
