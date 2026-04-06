"""关键字规则：命中备注等字段 → 一级/二级分类，并校验白名单。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from icostport.core.model import Transaction

if TYPE_CHECKING:
    from icostport.core.settings import Settings


def build_category_pairs(categories: dict[str, list[str]]) -> set[tuple[str, str]]:
    """由「一级 -> 二级列表」构建合法 (一级, 二级) 集合。"""
    pairs: set[tuple[str, str]] = set()
    for primary, secondaries in categories.items():
        for sec in secondaries:
            pairs.add((str(primary), str(sec)))
    return pairs


def is_allowed_pair(
    primary: str,
    secondary: str,
    allowed: set[tuple[str, str]],
    categories_nonempty: bool,
) -> bool:
    """若配置了非空 taxonomy，则 (一级, 二级) 必须在 allowed 中。"""
    if not categories_nonempty:
        return True
    return (primary, secondary) in allowed


def apply_keyword_rules(transactions: list[Transaction], settings: Settings) -> None:
    """
    按 ``settings.rules`` 顺序匹配：``keywords`` 在 ``note`` 中子串命中（大小写不敏感）则写入一级/二级。
    若 ``categories`` 非空，则校验 (primary, secondary) 须在白名单内，否则记警告并跳过该条规则结果。
    """
    pairs = build_category_pairs(settings.categories)
    nonempty = bool(settings.categories)

    for tx in transactions:
        if tx.primary_category is not None:
            continue
        note_l = tx.note.lower()
        for rule in settings.rules:
            kws = rule.keywords
            p, s = rule.primary, rule.secondary
            if not any(k.lower() in note_l for k in kws):
                continue
            if not is_allowed_pair(p, s, pairs, nonempty):
                logger.warning(
                    "规则命中但分类不在白名单内，已跳过: primary={!r} secondary={!r}",
                    p,
                    s,
                )
                continue
            tx.primary_category = p
            tx.secondary_category = s
            break
