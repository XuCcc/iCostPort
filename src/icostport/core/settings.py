"""加载 YAML 配置并构造运行时 Settings（无 pydantic）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from icostport.core.exceptions import ConfigError


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """浅层合并：override 覆盖 base 的同名键；嵌套 dict 递归合并。"""
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Settings:
    """运行时配置快照。"""

    categories: dict[str, list[str]]
    processing: dict[str, Any]
    rules: list[dict[str, Any]]
    ai: dict[str, Any]
    config_path: Path | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def minimal(cls) -> Settings:
        """无配置文件时的最小默认（便于开发与单测）。"""
        return cls(
            categories={},
            processing={},
            rules=[],
            ai={"enabled": False},
            config_path=None,
            raw={},
        )


def load_settings(path: Path | None) -> Settings:
    """
    从 YAML 文件加载配置。
    若 path 为 None，返回 :meth:`Settings.minimal`。
    """
    if path is None:
        return Settings.minimal()

    if not path.is_file():
        raise ConfigError(f"配置文件不存在: {path}")

    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 解析失败: {path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"无法读取配置: {path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"配置根节点必须是映射表: {path}")

    categories = data.get("categories") or {}
    if categories and not isinstance(categories, dict):
        raise ConfigError("`categories` 必须为「一级分类 -> 二级列表」映射")

    processing = data.get("processing") or {}
    if not isinstance(processing, dict):
        raise ConfigError("`processing` 必须为映射表")

    rules = data.get("rules") or []
    if not isinstance(rules, list):
        raise ConfigError("`rules` 必须为列表")

    ai = data.get("ai") or {}
    if not isinstance(ai, dict):
        raise ConfigError("`ai` 必须为映射表")

    return Settings(
        categories={str(k): list(v or []) for k, v in categories.items()},
        processing=processing,
        rules=rules,
        ai=ai,
        config_path=path,
        raw=data,
    )


def load_settings_with_local(
    main: Path | None,
    local: Path | None,
) -> Settings:
    """
    先加载主配置，再合并 ``config.local.yml``（若存在）。
    合并规则：嵌套 dict 递归合并，叶子覆盖。
    """
    base = load_settings(main)
    if local is None or not local.is_file():
        return base
    try:
        extra = yaml.safe_load(local.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:
        raise ConfigError(f"本地覆盖配置无效: {local}: {e}") from e
    if not isinstance(extra, dict):
        raise ConfigError(f"本地覆盖根节点必须为映射表: {local}")

    merged_raw = _deep_merge(base.raw, extra) if base.raw else dict(extra)
    # 与 load_settings 相同字段提取逻辑
    categories = merged_raw.get("categories") or base.categories
    processing = merged_raw.get("processing") or base.processing
    rules = merged_raw.get("rules") or base.rules
    ai = merged_raw.get("ai") or base.ai

    return Settings(
        categories=categories if isinstance(categories, dict) else base.categories,
        processing=processing if isinstance(processing, dict) else base.processing,
        rules=rules if isinstance(rules, list) else base.rules,
        ai=ai if isinstance(ai, dict) else base.ai,
        config_path=main or base.config_path,
        raw=merged_raw,
    )
