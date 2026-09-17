"""Needle response -> ParsedIntent mapping. Needle engine is stubbed; no network."""

import src.ai.needle_agent as na


class _FakeAgent:
    def __init__(self, response):
        self._response = response

    def complete(self, text, max_new_tokens=512):
        return self._response


def _with_response(monkeypatch, response):
    monkeypatch.setattr(na, "_make_agent", lambda schemas, system: _FakeAgent(response))


def test_empty_calls_is_unsupported(monkeypatch):
    _with_response(monkeypatch, {"function_calls": [], "confidence": 0.9})
    out = na.parse_with_needle("tell me a joke")
    assert out["status"] == "unsupported"


def test_chat_reply_maps_to_chat(monkeypatch):
    _with_response(
        monkeypatch,
        {
            "function_calls": [{"name": "chat_reply", "arguments": {"message": "Hello!"}}],
            "confidence": 0.95,
        },
    )
    out = na.parse_with_needle("hello")
    assert out["status"] == "chat" and out["message"] == "Hello!"


def test_ask_clarification_maps(monkeypatch):
    _with_response(
        monkeypatch,
        {
            "function_calls": [
                {"name": "ask_clarification", "arguments": {"question": "Which channel?"}}
            ],
            "confidence": 0.9,
        },
    )
    out = na.parse_with_needle("purge 10")
    assert out["status"] == "clarification_required"
    assert "Which channel" in out["question"]


def test_single_real_call_is_direct(monkeypatch):
    _with_response(
        monkeypatch,
        {
            "function_calls": [{"name": "create_channel", "arguments": {"name": "welcome"}}],
            "confidence": 0.93,
        },
    )
    out = na.parse_with_needle("create channel welcome")
    assert out["status"] == "direct_action"
    assert out["action"] == "create_channel"
    assert out["parameters"] == {"name": "welcome"}


def test_multi_call_is_plan_capped_at_five(monkeypatch):
    calls = [
        {"name": "send_message", "arguments": {"channel_id": "1", "content": "x"}} for _ in range(7)
    ]
    _with_response(monkeypatch, {"function_calls": calls, "confidence": 0.9})
    out = na.parse_with_needle("do many things")
    assert out["status"] == "action_plan"
    assert len(out["steps"]) == 5


def test_low_confidence_escalates_to_clarification(monkeypatch):
    _with_response(
        monkeypatch,
        {
            "function_calls": [{"name": "ban_member", "arguments": {"member_id": "1"}}],
            "confidence": 0.1,
        },
    )
    out = na.parse_with_needle("ban him", system=None)
    assert out["status"] == "clarification_required"


def test_engine_failure_is_rejected(monkeypatch):
    def _boom(schemas, system):
        raise RuntimeError("no engine")

    monkeypatch.setattr(na, "_make_agent", _boom)
    out = na.parse_with_needle("hi")
    assert out["status"] == "rejected"
