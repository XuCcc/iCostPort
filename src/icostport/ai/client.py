"""统一 HTTP 调用；只读配置中的 base_url、model、api_key_env 等。"""

from __future__ import annotations

import os
from typing import Any

import httpx

from loguru import logger


class AIClient:
    """兼容 OpenAI 风格 ``/v1/chat/completions`` 的客户端骨架。"""

    def __init__(self, ai_cfg: dict[str, Any]):
        self._cfg = ai_cfg

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        timeout: float | None = None,
    ) -> str:
        """
        发送 chat 请求并返回 ``choices[0].message.content`` 文本。
        若未配置 ``base_url`` 或无法读取 API Key，则返回空串并打日志。
        """
        base_url = (self._cfg.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            logger.debug("未配置 ai.base_url，跳过请求")
            return ""

        env_name = str(self._cfg.get("api_key_env", "OPENAI_API_KEY"))
        api_key = os.environ.get(env_name, "")
        if not api_key:
            logger.warning("环境变量 {} 未设置，无法调用 AI", env_name)
            return ""

        model = str(self._cfg.get("model", "gpt-4o-mini"))
        t = timeout if timeout is not None else float(self._cfg.get("timeout", 60.0))

        url = f"{base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=t) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error("AI 请求失败: {}", e)
            return ""

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as e:
            logger.error("AI 响应结构异常: {}", e)
            return ""
