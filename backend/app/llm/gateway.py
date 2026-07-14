"""LLM 网关：OpenAI 兼容 API（httpx 直连，不依赖 litellm）。

按 tier 路由模型，主模型失败时按 fallback 链逐个重试。
"""
import json
from typing import Any

import httpx

from app.llm.config import LLMRoutingConfig


class LLMGateway:
    """OpenAI 兼容 chat/completions 网关。

    M1 测试 mock httpx.AsyncClient.post，不真实调用 API；
    真实调用见 scripts/check_llm.py。
    """

    def __init__(
        self,
        routing: LLMRoutingConfig,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4",
    ) -> None:
        self.routing = routing
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tier: str | None = None,
        **kwargs: Any,
    ) -> str:
        """按 tier 路由模型，fallback 链重试，返回 assistant content。"""
        tier = tier or self.routing.default_tier
        models = self.routing.models_for_tier(tier)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=60) as client:
            for model in models:
                try:
                    resp = await client.post(
                        url,
                        headers=headers,
                        json={"model": model, "messages": messages, **kwargs},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                except Exception as exc:  # 任意失败 → 尝试下一个 fallback 模型
                    last_exc = exc
                    continue

        raise RuntimeError(
            f"All models failed for tier {tier!r} (tried {models}): {last_exc}"
        )

    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        tier: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """请求 JSON 结构化输出并解析为 dict。"""
        kwargs.setdefault("response_format", {"type": "json_object"})
        content = await self.complete(messages, tier=tier, **kwargs)
        return json.loads(content)
