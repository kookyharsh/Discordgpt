"""OpenRouter-compatible tool-calling provider.

This adapter deliberately returns the same normalized shape as the local
Needle engine so the dispatcher, confirmation UI, and policy checks remain the
source of truth for execution.
"""

from __future__ import annotations

import json
import os
from typing import Any

import aiohttp

from src.ai.needle_agent import PARSER_POLICY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _tool_definitions(tool_schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert the shared catalog schemas to OpenAI/OpenRouter tool format."""
    strict = os.getenv("OPENROUTER_STRICT_TOOLS", "false").lower() in {"1", "true", "yes"}
    result = []
    for schema in tool_schemas:
        parameters = schema.get("parameters") or {"type": "object", "properties": {}}
        function = {
            "name": schema["name"],
            "description": schema.get("description", "")[:2000],
            "parameters": parameters,
        }
        if strict:
            function["strict"] = True
        result.append({"type": "function", "function": function})
    return result


def _normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")
    message = choices[0].get("message") or {}
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        name = function.get("name")
        if not name:
            continue
        raw_arguments = function.get("arguments") or "{}"
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"OpenRouter returned invalid arguments for {name}.") from exc
        else:
            arguments = raw_arguments
        if not isinstance(arguments, dict):
            raise RuntimeError(f"OpenRouter arguments for {name} were not an object.")
        calls.append({"name": name, "arguments": arguments})

    # If a provider declines to emit a synthetic chat_reply call, preserve a
    # normal conversational response instead of treating it as an action miss.
    if not calls and message.get("content"):
        calls = [{"name": "chat_reply", "arguments": {"message": str(message["content"])}}]
    return {"function_calls": calls, "confidence": 0.9 if calls else 0.0}


async def parse_with_openrouter(
    text: str,
    tool_schemas: list[dict[str, Any]],
    system: str | None = None,
    *,
    timeout_seconds: float = 45,
) -> dict[str, Any]:
    """Call OpenRouter and return the provider-neutral Needle response shape."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    policy = PARSER_POLICY if not system else f"{PARSER_POLICY} {system}"
    body = {
        "model": model,
        "messages": [{"role": "system", "content": policy}, {"role": "user", "content": text}],
        "tools": _tool_definitions(tool_schemas),
        "tool_choice": "auto",
        "temperature": 0,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://discord-agent.local"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "Discord Agent"),
    }
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session, session.post(
        OPENROUTER_URL, headers=headers, json=body
    ) as response:
        payload = await response.json(content_type=None)
        if response.status >= 400:
            error = payload.get("error") if isinstance(payload, dict) else payload
            raise RuntimeError(f"OpenRouter HTTP {response.status}: {str(error)[:300]}")
    return _normalize_response(payload)
