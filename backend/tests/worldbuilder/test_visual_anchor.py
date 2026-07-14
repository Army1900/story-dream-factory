import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worldbuilder.visual_anchor import VisualAnchorService

def _mock_imagegen(return_bytes=b"fake-png"):
    ig = MagicMock()
    ig.generate = AsyncMock(return_value=return_bytes)
    return ig

@pytest.mark.asyncio
async def test_generate_style_reference():
    ig = _mock_imagegen()
    svc = VisualAnchorService(image_gateway=ig, image_store=MagicMock())
    visual_style = {"art_style": "油画", "palette": "冷蓝"}
    await svc.generate_style_reference("world-1", visual_style)
    assert ig.generate.await_count == 1
    # 确认 prompt 含风格锚
    call_kwargs = ig.generate.call_args.kwargs
    assert "油画" in call_kwargs["prompt"] or "油画" in ig.generate.call_args.args[0]

@pytest.mark.asyncio
async def test_generate_character_ref():
    ig = _mock_imagegen()
    store = MagicMock()
    store.save.return_value = "/data/images/w/c.png"
    svc = VisualAnchorService(image_gateway=ig, image_store=store)
    await svc.generate_character_ref("world-1", "c1", "艾伦，黑发疤脸的流亡骑士", {"art_style":"油画"})
    assert ig.generate.await_count == 1
    assert store.save.called

@pytest.mark.asyncio
async def test_style_prompt_includes_all_dims():
    ig = _mock_imagegen()
    svc = VisualAnchorService(image_gateway=ig, image_store=MagicMock())
    vs = {"art_style":"水彩","palette":"暖色","medium":"纸本","composition":"对称"}
    await svc.generate_style_reference("w1", vs)
    prompt = ig.generate.call_args.kwargs.get("prompt") or ig.generate.call_args.args[0]
    for v in vs.values():
        assert v in prompt
