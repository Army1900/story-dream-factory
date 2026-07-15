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
        """按 tier 路由模型，fallback 链重试，返回 assistant content。

        - httpx timeout 默认 120s（叙事/JSON 生成可能较慢）
        - max_tokens 默认 1024（避免部分模型返回空字符串），调用方可覆盖
        """
        tier = tier or self.routing.default_tier
        models = self.routing.models_for_tier(tier)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"

        # 默认 max_tokens，避免 LLM 因 token 上限返回空；调用方可通过 kwargs 覆盖
        kwargs.setdefault("max_tokens", 1024)

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=120) as client:
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
        """请求 JSON 结构化输出并解析为 dict。

        不用 response_format（coding/paas/v4 不支持），改用 prompt 引导 + 容错解析。
        若首次返回空或无法解析，追加更强指令重试一次。
        """
        # 不用 response_format（智谱 coding/paas/v4 不支持）
        kwargs.pop("response_format", None)

        # 在 system message 追加 JSON 要求
        patched = self._with_json_instruction(messages)

        content = await self.complete(patched, tier=tier, **kwargs)
        parsed = self._try_parse_json(content)
        if parsed is not None:
            return parsed

        # 重试一次：内容为空或无法解析，加强 prompt 后再试
        retry_messages = self._with_json_instruction(
            patched,
            extra=(
                "\n\n重要：上一次返回为空或不是合法 JSON。"
                "请务必返回一个非空的 JSON 对象，例如 "
                '{"intent":"...","action_type":"dialogue","target":"...","expectation":"...","dialogue":"..."}。'
                "只输出 JSON 本身，不要任何其它字符。"
            ),
        )
        retry_content = await self.complete(retry_messages, tier=tier, **kwargs)
        parsed = self._try_parse_json(retry_content)
        if parsed is not None:
            return parsed

        raise ValueError(
            f"Failed to parse JSON from LLM response (tried twice): "
            f"first={content[:120]!r} retry={retry_content[:120]!r}"
        )

    @staticmethod
    def _with_json_instruction(
        messages: list[dict[str, Any]], extra: str = ""
    ) -> list[dict[str, Any]]:
        """在 system message 追加 JSON 输出要求（若无 system 则插入一个）。"""
        suffix = (
            "\n\n必须只输出合法 JSON，不要 markdown 代码块，不要解释文字。" + extra
        )
        patched: list[dict[str, Any]] = []
        injected = False
        for m in messages:
            if m["role"] == "system" and not injected:
                patched.append({**m, "content": m["content"] + suffix})
                injected = True
            else:
                patched.append(m)
        if not injected:
            patched.insert(0, {"role": "system", "content": "你是 JSON 生成器。" + suffix})
        return patched

    @staticmethod
    def _try_parse_json(content: str) -> dict | None:
        """容错解析：空→None；直接 parse→去 markdown→提取 {...} 块。"""
        if not content or not content.strip():
            return None
        try:
            result = json.loads(content)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        import re
        # 去 markdown 代码块
        cleaned = re.sub(r"```(?:json)?\s*", "", content)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # 提取第一个 {...} 块（兼容嵌套：优先最大匹配）
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        # 退而求其次：最内层 {...}
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        return None
