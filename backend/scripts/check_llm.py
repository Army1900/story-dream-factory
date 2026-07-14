"""手动验证 LLM 网关真实调用（httpx 直连，不需 litellm）。

需配置 ZHIPU_API_KEY（或 OPENAI_API_KEY）。

运行：.venv/Scripts/python.exe scripts/check_llm.py
"""
import asyncio
import json
import sys

from app.config import get_settings
from app.llm.config import LLMRoutingConfig, TierConfig
from app.llm.gateway import LLMGateway


def build_gateway() -> LLMGateway:
    settings = get_settings()
    api_key = settings.zhipu_api_key or settings.openai_api_key
    if not api_key:
        print(
            "错误：未配置 ZHIPU_API_KEY / OPENAI_API_KEY（请填写 .env）",
            file=sys.stderr,
        )
        sys.exit(1)
    routing = LLMRoutingConfig(
        tiers={
            "tier1": TierConfig(model="glm-4-plus", fallback_models=["glm-4-flash"]),
            "tier2": TierConfig(model="glm-4-plus"),
            "tier3": TierConfig(model="glm-4-flash"),
        },
        default_tier="tier1",
    )
    return LLMGateway(routing=routing, api_key=api_key)


async def main() -> None:
    gw = build_gateway()

    print("== 文本补全 ==")
    text = await gw.complete(
        messages=[{"role": "user", "content": "用一句话描述暴风雨中的中世纪小镇。"}],
    )
    print(text)

    print("\n== JSON 结构化输出 ==")
    data = await gw.complete_json(
        messages=[
            {"role": "system", "content": "你是角色生成器，只输出 JSON 对象。"},
            {
                "role": "user",
                "content": "生成一个奇幻角色，包含字段：name, role, trait",
            },
        ],
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
