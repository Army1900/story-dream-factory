from typing import Any

import httpx

from app.config import get_settings


def build_prompt(visual_style: dict, subject: str) -> str:
    """把世界风格锚作为固定前缀，拼到主体描述前——保证跨阶段风格一致。"""
    parts: list[str] = []
    if visual_style.get("art_style"):
        parts.append(f"画风: {visual_style['art_style']}")
    if visual_style.get("palette"):
        parts.append(f"色调: {visual_style['palette']}")
    if visual_style.get("medium"):
        parts.append(f"媒介: {visual_style['medium']}")
    if visual_style.get("composition"):
        parts.append(f"构图: {visual_style['composition']}")
    style_prefix = "，".join(parts)
    return f"{style_prefix}。{subject}" if style_prefix else subject


async def zhipu_generate(prompt: str, seed: int, **kwargs: Any) -> bytes:
    """智谱 CogView 生图（示例实现，需真实密钥）。

    M1 测试不调用此函数（mock）；真实调用见 scripts/check_imagegen.py。
    """
    settings = get_settings()
    api_key = settings.zhipu_api_key
    model = settings.zhipu_image_model
    # 注意：此处为示例 HTTP 调用结构，实际 endpoint/认证以智谱文档为准。
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://open.bigmodel.cn/api/paas/v4/images/generations",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "prompt": prompt, "seed": seed},
        )
        resp.raise_for_status()
        # 真实返回含图片 URL；这里简化为返回字节（实际应下载 URL）
        data = resp.json()
        img_url = data["data"][0]["url"]
        img = await client.get(img_url)
        return img.content


class ImageGateway:
    """生图网关：风格锚注入 + 种子固定 + 多 provider 抽象。"""

    def __init__(self, provider: str | None = None):
        self.provider = provider or get_settings().imagegen_provider

    async def generate(self, prompt: str, seed: int = 0, **kwargs: Any) -> bytes:
        if self.provider == "zhipu":
            return await zhipu_generate(prompt=prompt, seed=seed, **kwargs)
        raise ValueError(f"Unknown image provider: {self.provider}")
