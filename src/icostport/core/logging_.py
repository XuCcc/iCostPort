"""loguru 控制台/文件输出，与 CLI verbose 联动。"""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger


def configure_logging(*, verbose: bool = False, log_file: str | None = None) -> None:
    """
    配置全局日志：默认仅控制台；verbose 时降低级别；可选文件 sink。
    """
    logger.remove()
    level: str | int = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )
    if log_file:
        logger.add(
            log_file,
            level=level,
            rotation="10 MB",
            encoding="utf-8",
        )


def get_logger() -> Any:
    """返回 loguru logger（便于类型提示较弱的场景）。"""
    return logger
