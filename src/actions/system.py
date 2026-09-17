"""System tools: Needle control tools + catalog export.

Side-effect import registers nothing into ActionRegistry (these are
Needle engine tools, not Discord actions), but keeps the
ask_clarification / chat_reply behavior from the old needle_tools module.
"""

from __future__ import annotations

import needle


@needle.tool
def ask_clarification(question: str) -> str:
    """Ask the user a clarifying question when details or target parameters are ambiguous or missing.

    Args:
        question: Concise explanation of what detail or choice is missing.
    """
    return f"Clarification requested: {question}"


@needle.tool
def chat_reply(message: str) -> str:
    """Send a friendly conversational response or explanation to the user when no Discord operation is required.

    Args:
        message: Conversational message to display to the user.
    """
    return message


def export_tools_json(filepath: str = "tools/discord_tools.json"):
    """Export the registered Discord action catalog to JSON."""
    import json

    from src.actions.registry import ActionRegistry

    schemas = []
    for act in ActionRegistry.get_all():
        schemas.append(
            {
                "name": act.type,
                "description": act.description,
                "parameters": act.input_schema.model_json_schema(),
                "risk_level": act.risk_level.value,
                "confirmation_policy": act.confirmation_policy.value,
            }
        )
    with open(filepath, "w") as f:
        json.dump(schemas, f, indent=2)
