import pytest
from unittest.mock import AsyncMock, patch

from app.imagegen.gateway import ImageGateway, build_prompt


def test_build_prompt_prepends_style_anchor():
    visual_style = {"art_style": "oil-painting", "palette": "dark", "negative_prompt": "blurry"}
    prompt = build_prompt(visual_style=visual_style, subject="艾伦站在酒馆前")
    assert "oil-painting" in prompt
    assert "艾伦站在酒馆前" in prompt
    assert "dark" in prompt


def test_build_prompt_without_style():
    prompt = build_prompt(visual_style={}, subject="一个场景")
    assert "一个场景" in prompt


@pytest.mark.asyncio
async def test_generate_returns_image_bytes():
    gw = ImageGateway(provider="zhipu")
    fake = AsyncMock(return_value=b"fake-png-bytes")
    with patch("app.imagegen.gateway.zhipu_generate", fake):
        data = await gw.generate(prompt="p", seed=42)
    assert data == b"fake-png-bytes"
    fake.assert_awaited_once()
    # 确认 seed 被传入
    assert fake.call_args.kwargs["seed"] == 42


@pytest.mark.asyncio
async def test_generate_unknown_provider_raises():
    gw = ImageGateway(provider="unknown")
    with pytest.raises(ValueError):
        await gw.generate(prompt="p", seed=1)
