import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.llm.config import LLMRoutingConfig, TierConfig
from app.llm.gateway import LLMGateway


def _make_routing() -> LLMRoutingConfig:
    return LLMRoutingConfig(
        tiers={
            "tier1": TierConfig(
                model="glm-4-plus",
                fallback_models=["glm-4-flash"],
            ),
        },
        default_tier="tier1",
    )


def _mock_response(content: str) -> Mock:
    """构造一个能被 raise_for_status()/json() 调用的假 response。"""
    resp = Mock()
    resp.raise_for_status = Mock(return_value=None)
    resp.json = Mock(
        return_value={"choices": [{"message": {"content": content}}]}
    )
    return resp


@pytest.mark.asyncio
async def test_complete_returns_text():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    mock_post = AsyncMock(return_value=_mock_response("你好，世界"))

    with patch("httpx.AsyncClient.post", mock_post):
        text = await gw.complete(messages=[{"role": "user", "content": "hi"}])

    assert text == "你好，世界"
    mock_post.assert_awaited_once()
    # 验证主模型被发送
    sent = mock_post.call_args.kwargs["json"]
    assert sent["model"] == "glm-4-plus"
    assert sent["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_complete_falls_back_on_error():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    # 第一次（主模型）抛错 → 第二次（fallback）成功
    mock_post = AsyncMock(
        side_effect=[httpx.HTTPError("primary down"), _mock_response("from fallback")]
    )

    with patch("httpx.AsyncClient.post", mock_post):
        text = await gw.complete(messages=[{"role": "user", "content": "hi"}])

    assert text == "from fallback"
    assert mock_post.await_count == 2
    # 第二次调用应发送 fallback 模型
    second_call = mock_post.await_args_list[1]
    assert second_call.kwargs["json"]["model"] == "glm-4-flash"


@pytest.mark.asyncio
async def test_complete_json_parses_structured_output():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    payload = {"name": "艾伦", "role": "游侠", "trait": "沉默寡言"}
    mock_post = AsyncMock(
        return_value=_mock_response(json.dumps(payload, ensure_ascii=False))
    )

    with patch("httpx.AsyncClient.post", mock_post):
        result = await gw.complete_json(
            messages=[{"role": "user", "content": "生成一个角色"}]
        )

    assert result == payload
    # 验证 response_format 被注入请求体
    sent = mock_post.call_args.kwargs["json"]
    assert sent["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_complete_all_models_fail_raises_runtime_error():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    mock_post = AsyncMock(side_effect=httpx.HTTPError("all down"))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(RuntimeError):
            await gw.complete(messages=[{"role": "user", "content": "hi"}])

    # tier1 主+fallback 各尝试一次
    assert mock_post.await_count == 2
