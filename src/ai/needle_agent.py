from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("discord_agent.needle")

CONFIDENCE_THRESHOLD = float(os.getenv("NEEDLE_CONFIDENCE_THRESHOLD", "0.5"))
ENGINE_TIMEOUT_SECONDS = float(os.getenv("NEEDLE_ENGINE_TIMEOUT", "90"))
# The native engine binds one active session per process and its calls block
# for seconds (init is cheap; first complete() per binding is not). Never run
# it on the event loop: one worker + single-flight lock keeps the Discord
# gateway heartbeat alive and serializes native access.
_AGENT_LOCK = asyncio.Lock()
TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
CATALOG_JSON = os.getenv("NEEDLE_TOOLS_JSON", str(TOOLS_DIR / "discord_tools.json"))
CATALOG_HASH_FILE = TOOLS_DIR / ".catalog_hash"

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


def catalog_fingerprint() -> str:
    """Stable hash of the live tool catalog (names + descriptions + schemas).

    The engine caches retrieval embeddings per index file, so the index path
    embeds this fingerprint: any registry change (new tool, new wording)
    automatically busts the cache instead of serving stale embeddings.
    """
    import hashlib
    import json

    from src.actions.registry import ActionRegistry

    entries = []
    for act in sorted(ActionRegistry.get_all(), key=lambda a: a.type):
        try:
            schema = act.input_schema.model_json_schema()
        except Exception:
            schema = {}
        entries.append({"name": act.type, "description": act.description, "parameters": schema})
    return hashlib.sha1(json.dumps(entries, sort_keys=True).encode()).hexdigest()[:12]


def resolve_index_path() -> str:
    """Index file for the current catalog; the engine creates it on demand.

    Honors NEEDLE_TOOL_INDEX as an explicit override, otherwise embeds the
    catalog fingerprint so registry changes bust the embedding cache.
    """
    override = os.getenv("NEEDLE_TOOL_INDEX")
    if override:
        return override
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    return str(TOOLS_DIR / f"tools.{catalog_fingerprint()}.idx")


def refresh_artifacts() -> dict[str, Any]:
    """Regenerate discord_tools.json + fingerprint; returns status info.

    Safe to run at startup: only writes when the catalog changed.
    """
    from src.actions.system import export_tools_json

    fingerprint = catalog_fingerprint()
    previous = ""
    try:
        previous = CATALOG_HASH_FILE.read_text().strip()
    except OSError:
        pass
    changed = previous != fingerprint
    if changed:
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        export_tools_json(str(CATALOG_JSON))
        CATALOG_HASH_FILE.write_text(fingerprint)
    return {"changed": changed, "fingerprint": fingerprint, "previous": previous or None}


def check_artifacts_stale() -> None:
    """Refresh the tool catalog artifacts, warning when they changed."""
    try:
        info = refresh_artifacts()
    except Exception as e:
        logger.warning("Tool catalog refresh skipped: %s", e)
        return
    if info["changed"]:
        if info["previous"] is None:
            logger.info("Tool catalog indexed (%s).", info["fingerprint"])
        else:
            logger.warning(
                "Tool catalog changed (%s -> %s); discord_tools.json regenerated and "
                "the retrieval index will rebuild on the next parse.",
                info["previous"],
                info["fingerprint"],
            )


def _make_agent(tool_schemas: list[dict[str, Any]], system: str | None):
    import needle  # lazy: engine binary downloads on first Needle() use

    kwargs: dict[str, Any] = {"tools": tool_schemas}
    if system:
        kwargs["system"] = system
    if len(tool_schemas) > 5:
        kwargs["tool_index_path"] = resolve_index_path()
    return needle.Needle(**kwargs)


def _run_engine_blocking(
    tool_schemas: list[dict[str, Any]], system: str | None, text: str, max_new_tokens: int
) -> dict[str, Any]:
    """Build a fresh agent and complete one turn. Runs in a worker thread.

    A fresh binding per prompt is load-bearing: the native session carries
    state across complete() calls, so sharing one agent leaks prior prompts'
    facts into later parses.
    """
    agent = _make_agent(tool_schemas, system)
    try:
        return agent.complete(text, max_new_tokens=max_new_tokens)
    finally:
        try:
            agent.close()
        except Exception:
            pass


async def prewarm_engine() -> None:
    """Fault in the engine binary + tool index at startup (background)."""
    try:
        tool_schemas = build_tool_schemas()
        await asyncio.to_thread(_make_agent, tool_schemas, None)
    except Exception as e:
        logger.warning("Engine prewarm skipped: %s", e)


async def parse_with_needle(
    text: str,
    allowed_actions: list[str] | None = None,
    system: str | None = None,
    max_new_tokens: int = 512,
) -> dict[str, Any]:
    """One Needle turn -> normalized ParsedIntent dict.

    Async: the blocking engine runs in a worker thread under a single-flight
    lock, so the Discord heartbeat is never starved. Times out instead of
    hanging the interaction.

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
        async with _AGENT_LOCK:
            response = await asyncio.wait_for(
                asyncio.to_thread(_run_engine_blocking, tool_schemas, system, text, max_new_tokens),
                timeout=ENGINE_TIMEOUT_SECONDS,
            )
    except TimeoutError:
        logger.warning("Needle engine timed out after %ss", ENGINE_TIMEOUT_SECONDS)
        return {"status": "rejected", "reason": "Parser timed out. Please try again."}
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
