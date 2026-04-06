"""加载 YAML 配置并构造运行时 Settings（PyYAML + pydantic 校验）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from icostport.core.exceptions import ConfigError


def _resolve_config_path(explicit: Path | None) -> Path | None:
    """
    解析配置路径查找顺序：
    1) CLI --config；
    2) 环境变量 ICOSTPORT_CONFIG；
    3) 当前目录 config.yml；
    4) 用户目录 ~/.config/icostport/config.yml（可选）。
    """
    if explicit is not None:
        return explicit

    env_path = os.getenv("ICOSTPORT_CONFIG")
    if env_path:
        return Path(env_path).expanduser()

    cwd_default = Path.cwd() / "config.yml"
    if cwd_default.is_file():
        return cwd_default

    user_default = Path.home() / ".config" / "icostport" / "config.yml"
    if user_default.is_file():
        return user_default
    return None


def _read_yaml(path: Path) -> dict[str, Any]:
    """读取 YAML 并确保根节点为映射表。"""
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 解析失败: {path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"无法读取配置: {path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"配置根节点必须是映射表: {path}")
    return data


class RuleConfig(BaseModel):
    """关键字规则配置。"""

    keywords: list[str] = Field(default_factory=list)
    primary: str
    secondary: str

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _keywords_not_empty(self) -> RuleConfig:
        if not self.keywords:
            raise ValueError("`rules[].keywords` 不能为空列表")
        return self


class DedupeConfig(BaseModel):
    """去重配置。"""

    enabled: bool = True
    on_duplicate: str = "keep_first"

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _check_on_duplicate(self) -> DedupeConfig:
        if self.on_duplicate not in {"keep_first", "keep_last"}:
            raise ValueError("`processing.dedupe.on_duplicate` 仅支持 keep_first/keep_last")
        return self


class ProcessingConfig(BaseModel):
    """处理阶段配置。"""

    dedupe: DedupeConfig = Field(default_factory=DedupeConfig)
    filter: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class AIConfig(BaseModel):
    """AI 配置。"""

    enabled: bool = False
    provider: str = "openai"
    base_url: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    only_if_uncategorized: bool = True
    max_items: int = 0
    timeout: float = 30.0

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _numeric_constraints(self) -> AIConfig:
        if self.max_items < 0:
            raise ValueError("`ai.max_items` 不能为负数")
        if self.timeout <= 0:
            raise ValueError("`ai.timeout` 必须大于 0")
        return self


class Settings(BaseModel):
    """运行时配置快照。"""

    categories: dict[str, list[str]] = Field(default_factory=dict)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    rules: list[RuleConfig] = Field(default_factory=list)
    ai: AIConfig = Field(default_factory=AIConfig)
    config_path: Path | None
    raw: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_taxonomy_constraints(self) -> Settings:
        # 一级分类可空；若非空则每个一级必须至少有一个二级。
        if self.categories:
            for primary, secondaries in self.categories.items():
                if not isinstance(secondaries, list) or not secondaries:
                    raise ValueError(
                        f"`categories.{primary}` 必须为非空二级分类列表（分类白名单约束）"
                    )

            allowed_pairs = {
                (primary, secondary)
                for primary, secondaries in self.categories.items()
                for secondary in secondaries
            }
            for idx, rule in enumerate(self.rules):
                pair = (rule.primary, rule.secondary)
                if pair not in allowed_pairs:
                    raise ValueError(
                        f"`rules[{idx}]` 的分类 ({rule.primary}, {rule.secondary}) 不在 categories 白名单内"
                    )
        return self

    @classmethod
    def minimal(cls) -> Settings:
        """无配置文件时的最小默认（便于开发与单测）。"""
        return cls(
            categories={},
            processing=ProcessingConfig(),
            rules=[],
            ai=AIConfig(),
            config_path=None,
            raw={},
        )


def load_settings(path: Path | None) -> Settings:
    """
    从 YAML 文件加载配置。
    若 path 为 None，按默认顺序查找配置；都不存在则返回最小默认配置。
    """
    resolved = _resolve_config_path(path)
    if resolved is None:
        return Settings.minimal()

    if not resolved.is_file():
        raise ConfigError(f"配置文件不存在: {resolved}")

    data = _read_yaml(resolved)
    try:
        return Settings(
            categories={str(k): [str(x) for x in (v or [])] for k, v in (data.get("categories") or {}).items()},
            processing=ProcessingConfig.model_validate(data.get("processing") or {}),
            rules=[RuleConfig.model_validate(x) for x in (data.get("rules") or [])],
            ai=AIConfig.model_validate(data.get("ai") or {}),
            config_path=resolved,
            raw=data,
        )
    except ValidationError as e:
        raise ConfigError(f"配置校验失败: {resolved}: {e}") from e
    except (TypeError, ValueError) as e:
        raise ConfigError(f"配置校验失败: {resolved}: {e}") from e


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
    extra = _read_yaml(local)

    def _deep_merge(base_raw: dict[str, Any], override_raw: dict[str, Any]) -> dict[str, Any]:
        out = dict(base_raw)
        for k, v in override_raw.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    merged_raw = _deep_merge(base.raw, extra) if base.raw else dict(extra)
    try:
        return Settings(
            categories={
                str(k): [str(x) for x in (v or [])]
                for k, v in (merged_raw.get("categories") or {}).items()
            },
            processing=ProcessingConfig.model_validate(merged_raw.get("processing") or {}),
            rules=[RuleConfig.model_validate(x) for x in (merged_raw.get("rules") or [])],
            ai=AIConfig.model_validate(merged_raw.get("ai") or {}),
            config_path=main or base.config_path,
            raw=merged_raw,
        )
    except ValidationError as e:
        raise ConfigError(f"本地覆盖配置校验失败: {local}: {e}") from e
    except (TypeError, ValueError) as e:
        raise ConfigError(f"本地覆盖配置校验失败: {local}: {e}") from e
