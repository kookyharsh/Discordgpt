import pytest

from src.ai import needle_agent
from src.ai.openrouter_agent import _normalize_response, _tool_definitions


def test_openrouter_tool_shape_preserves_catalog_schema():
    tools = _tool_definitions(
        [
            {
                "name": "create_channel",
                "description": "Creates a channel.",
                "parameters": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        ]
    )
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "create_channel"
    assert tools[0]["function"]["parameters"]["properties"]["name"]["type"] == "string"


def test_openrouter_tool_call_normalization():
    result = _normalize_response(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "create_channel",
                                    "arguments": '{"name":"harsh","type":"voice"}',
                                }
                            }
                        ]
                    }
                }
            ]
        }
    )
    assert result == {
        "function_calls": [
            {"name": "create_channel", "arguments": {"name": "harsh", "type": "voice"}}
        ],
        "confidence": 0.9,
    }


@pytest.mark.asyncio
async def test_openrouter_provider_uses_normalized_result(monkeypatch):
    async def fake_openrouter(text, schemas, system):
        return {
            "function_calls": [
                {"name": "create_channel", "arguments": {"name": "harsh", "type": "voice"}}
            ],
            "confidence": 0.9,
        }

    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setattr("src.ai.openrouter_agent.parse_with_openrouter", fake_openrouter)
    out = await needle_agent.parse_with_needle("create a voice channel named harsh")
    assert out["status"] == "direct_action"
    assert out["action"] == "create_channel"
    assert out["parameters"]["type"] == "voice"
