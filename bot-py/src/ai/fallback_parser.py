import re
from typing import Any


class FallbackParser:
    @staticmethod
    def parse(prompt: str) -> dict[str, Any] | None:
        normalized = prompt.strip().lower()

        # Match "create channel <name>"
        match = re.search(r"create (?:a )?(?:text )?channel (?:called |named )?([a-z0-9-_]+)", normalized)
        if match:
            return {
                "action": "create_channel",
                "parameters": {"name": match.group(1), "type": "text"},
            }

        # Match "delete channel <id>"
        match = re.search(r"delete channel ([0-9]+)", normalized)
        if match:
            return {
                "action": "delete_channel",
                "parameters": {"channel_id": match.group(1)},
            }

        return None
