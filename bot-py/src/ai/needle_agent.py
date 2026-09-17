from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("discord_agent.needle")

CONFIDENCE_THRESHOLD = float(os.getenv("NEEDLE_CONFIDENCE_THRESHOLD", "0.5"))
TOOL_INDEX_PATH = os.getenv(
    "NEEDLE_TOOL_INDEX", str(Path(__file__).resolve().parents[2] / "tools.idx")
)

_SYNTHETIC_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "ask_clarification",
        "description": (
            "Ask the user a clarifying question when a required target or detail "
            "is missing or ambiguous. Call ONLY when you cannot fill a required argument."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Concise question stating exactly what detail is missing.",
                    "maxLength": 500,
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "chat_reply",
        "description": (
            "Send a friendly conversational reply when NO Discord server operation "
            "is required (greetings, questions, advice, explanations)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Conversational reply, under 1500 chars. Never claim an action was executed.",
                    "maxLength": 1500,
                }
            },
            "required": ["message"],
        },
    },
]


def build_tool_schemas(allowed_actions: list[str] | None = None) -> list[dict[str, Any]]:
    """Raw JSON schemas for Needle: registry actions (filtered) + 2 synthetics."""
    from src.actions.registry import ActionRegistry

    schemas: list[dict[str, Any]] = []
    for act in ActionRegistry.get_all():
        if act.type in ("ask_clarification", "chat_reply"):
            continue
        if allowed_actions and act.type not in allowed_actions:
            continue
        try:
            params = act.input_schema.model_json_schema()
        except Exception:
            params = {"type": "object", "properties": {}}
        # Strip pydantic titles to keep context small; keep constraints.
        params.pop("title", None)
        schemas.append({"name": act.type, "description": act.description, "parameters": params})
    return schemas + _SYNTHETIC_SCHEMAS


def _make_agent(tool_schemas: list[dict[str, Any]], system: str | None):
    import needle  # lazy: engine binary downloads on first Needle() use

    kwargs: dict[str, Any] = {"tools": tool_schemas}
    if system:
        kwargs["system"] = system
    if len(tool_schemas) > 5:
        kwargs["tool_index_path"] = TOOL_INDEX_PATH
    return needle.Needle(**kwargs)


def parse_with_needle(
    text: str,
    allowed_actions: list[str] | None = None,
    system: str | None = None,
    max_new_tokens: int = 512,
) -> dict[str, Any]:
    """One Needle turn -> normalized ParsedIntent dict.

    Returns one of:
      {"status": "direct_action", "action": str, "parameters": dict, "confidence": float|None}
      {"status": "action_plan", "steps": [{id, action, parameters}], "confidence": ...}
      {"status": "clarification_required", "question": str, "confidence": ...}
      {"status": "chat", "message": str, "confidence": ...}
      {"status": "unsupported", "reason": str, "confidence": ...}
      {"status": "rejected", "reason": str}  # engine/transport failure
    """
    tool_schemas = build_tool_schemas(allowed_actions)
    try:
        agent = _make_agent(tool_schemas, system)
        response = agent.complete(text, max_new_tokens=max_new_tokens)
    except Exception as err:
        logger.warning("Needle complete() failed: %s", str(err)[:200])
        return {"status": "rejected", "reason": f"Parser unavailable: {str(err)[:180]}"}

    confidence = response.get("confidence")
    calls = response.get("function_calls") or []
    if not calls:
        # Empty call = refusal. Suppressed (low-conf) calls carry a hint.
        suppressed = response.get("suppressed_calls") or []
        hint = ""
        if suppressed:
            try:
                hint = f" (closest match: {suppressed[0].get('name', '?')})"
            except Exception:
                pass
        return {
            "status": "unsupported",
            "reason": f"I couldn't match that to a supported server action{hint}. Try something concrete like 'Create channel welcome'.",
            "confidence": confidence,
        }

    # Confidence gate: below threshold -> ask user instead of executing.
    if confidence is not None and confidence < CONFIDENCE_THRESHOLD:
        first = calls[0]
        return {
            "status": "clarification_required",
            "question": (
                f"I'm not confident I understood ({confidence:.2f}). "
                f"Did you mean '{first.get('name')}' with {first.get('arguments', {})}? "
                "Please rephrase or confirm."
            ),
            "confidence": confidence,
        }

    if len(calls) == 1 and calls[0].get("name") == "ask_clarification":
        args = calls[0].get("arguments", {}) or {}
        return {
            "status": "clarification_required",
            "question": str(args.get("question", "Please provide more details."))[:500],
            "confidence": confidence,
        }
    if len(calls) == 1 and calls[0].get("name") == "chat_reply":
        args = calls[0].get("arguments", {}) or {}
        return {
            "status": "chat",
            "message": str(args.get("message", "How can I help?"))[:1900],
            "confidence": confidence,
        }
    # Filter out any synthetic mixed into a multi-call (shouldn't happen).
    real = [c for c in calls if c.get("name") not in ("ask_clarification", "chat_reply")]
    if not real:
        return {
            "status": "unsupported",
            "reason": "No actionable call produced.",
            "confidence": confidence,
        }
    if len(real) == 1:
        return {
            "status": "direct_action",
            "action": real[0]["name"],
            "parameters": real[0].get("arguments", {}) or {},
            "confidence": confidence,
        }
    steps = [
        {"id": str(i + 1), "action": c["name"], "parameters": c.get("arguments", {}) or {}}
        for i, c in enumerate(real[:5])
    ]
    return {"status": "action_plan", "steps": steps, "confidence": confidence}
