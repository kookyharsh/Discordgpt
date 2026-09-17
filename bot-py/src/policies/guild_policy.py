from typing import Any


class GuildPolicyEngine:
    @staticmethod
    def check_action_allowed(
        action_type: str,
        settings: Any | None = None
    ) -> tuple[bool, str | None]:
        if not settings:
            return True, None

        if getattr(settings, "enabled", True) is False:
            return False, "Bot interactions are currently disabled for this server."

        disabled_actions: list[str] = getattr(settings, "disabledActions", []) or []
        if action_type in disabled_actions:
            return False, f"Action '{action_type}' has been disabled by server administrators."

        allowed_actions: list[str] = getattr(settings, "allowedActions", []) or []
        if allowed_actions and action_type not in allowed_actions:
            return False, f"Action '{action_type}' is not in the server's allowed actions list."

        return True, None
