"""pytest 公共夹具与路径初始化。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def fixtures_dir() -> Path:
    """返回测试夹具目录路径。"""
    return Path(__file__).resolve().parent / "fixtures"
