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
            messages=[{"role": "system", "content": "你是角色生成器"}, {"role": "user", "content": "生成一个角色"}]
        )

    assert result == payload
    sent = mock_post.call_args.kwargs["json"]
    assert sent["max_tokens"] == 1024  # 默认 max_tokens 被透传到请求体
    assert "JSON" in sent["messages"][0]["content"]  # JSON 输出指令追加到 system message
    assert "response_format" not in sent  # 不再用 response_format（coding/paas/v4 不支持）
    mock_post.assert_awaited_once()  # 解析成功，无需重试


@pytest.mark.asyncio
async def test_complete_passes_max_tokens_override():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    mock_post = AsyncMock(return_value=_mock_response("ok"))

    with patch("httpx.AsyncClient.post", mock_post):
        await gw.complete(messages=[{"role": "user", "content": "hi"}], max_tokens=512)

    sent = mock_post.call_args.kwargs["json"]
    assert sent["max_tokens"] == 512  # 调用方覆盖生效


@pytest.mark.asyncio
async def test_complete_json_retries_on_empty_then_succeeds():
    """首次返回空字符串 → 重试一次（更强 prompt）→ 成功解析。"""
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    payload = {"intent": "质问", "action_type": "dialogue"}
    mock_post = AsyncMock(
        side_effect=[
            _mock_response(""),  # 首次空
            _mock_response(json.dumps(payload, ensure_ascii=False)),  # 重试成功
        ]
    )

    with patch("httpx.AsyncClient.post", mock_post):
        result = await gw.complete_json(messages=[{"role": "system", "content": "你是决策器"}])

    assert result == payload
    assert mock_post.await_count == 2  # 重试了一次
    # 重试的 system message 应含更强的 JSON 提示
    retry_sent = mock_post.await_args_list[1].kwargs["json"]
    assert "非空" in retry_sent["messages"][0]["content"]


@pytest.mark.asyncio
async def test_complete_json_raises_when_retry_also_fails():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    mock_post = AsyncMock(
        return_value=_mock_response("not a json at all")  # 两次都无法解析
    )

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(ValueError):
            await gw.complete_json(messages=[{"role": "system", "content": "你是决策器"}])

    assert mock_post.await_count == 2  # 重试了一次后报错


@pytest.mark.asyncio
async def test_complete_all_models_fail_raises_runtime_error():
    gw = LLMGateway(routing=_make_routing(), api_key="sk-test")
    mock_post = AsyncMock(side_effect=httpx.HTTPError("all down"))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(RuntimeError):
            await gw.complete(messages=[{"role": "user", "content": "hi"}])

    # tier1 主+fallback 各尝试一次
    assert mock_post.await_count == 2
