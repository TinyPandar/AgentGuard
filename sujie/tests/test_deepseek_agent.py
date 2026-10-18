import json

import httpx
import pytest
from sujie_demo_agent.bailian_agent import ModelProtocolError
from sujie_demo_agent.deepseek_agent import DeepSeekChatModel, DeepSeekCredentials

KEY = "sk-" + "fake-test-key" * 3


def test_credentials_are_private_and_endpoint_is_fixed(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    credentials = DeepSeekCredentials.from_env()
    assert KEY not in repr(credentials)
    assert credentials.base_url == "https://api.deepseek.com"
    with pytest.raises(TypeError):
        DeepSeekCredentials(KEY, base_url="https://other.invalid")
    with pytest.raises(ValueError):
        DeepSeekCredentials("invalid")
    with pytest.raises(ValueError):
        DeepSeekChatModel(credentials, model="qwen-plus")


@pytest.mark.asyncio
async def test_tool_call_round_trip_and_usage(monkeypatch):
    captured = []
    replies = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "operations__read_file",
                        "arguments": '{"path":"report.txt"}',
                    },
                }
            ],
        },
        {"role": "assistant", "content": "已核查"},
    ]

    async def post(self, url, **kwargs):
        captured.append((url, kwargs))
        return httpx.Response(
            200, json={"choices": [{"message": replies.pop(0)}], "usage": {"total_tokens": 12}}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    model = DeepSeekChatModel(DeepSeekCredentials(KEY))
    messages = [{"role": "user", "content": "核查报告"}]
    tools = [{"type": "function", "function": {"name": "operations__read_file"}}]
    response = await model.complete(messages, tools)
    messages.extend([response, {"role": "tool", "tool_call_id": "call_1", "content": "ok"}])
    assert (await model.complete(messages, tools))["content"] == "已核查"
    assert model.transport_attempts == 2
    assert sum(item["total_tokens"] for item in model.usage) == 24
    for url, request in captured:
        assert url == "https://api.deepseek.com/chat/completions"
        assert request["headers"]["Authorization"] == "Bearer " + KEY
        assert request["json"]["thinking"] == {"type": "disabled"}
        assert KEY not in json.dumps(request["json"])
    assert captured[1][1]["json"]["messages"][-1]["tool_call_id"] == "call_1"


@pytest.mark.asyncio
async def test_error_and_model_egress_do_not_expose_key(monkeypatch):
    async def post(self, url, **kwargs):
        return httpx.Response(401, text=KEY)

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    model = DeepSeekChatModel(DeepSeekCredentials(KEY))
    with pytest.raises(ModelProtocolError, match="^DEEPSEEK_HTTP_401$"):
        await model.complete([{"role": "user", "content": "test"}], [])
    with pytest.raises(ModelProtocolError, match="MODEL_EGRESS_CREDENTIAL"):
        await model.complete([{"role": "user", "content": KEY}], [])
    assert model.transport_attempts == 1
