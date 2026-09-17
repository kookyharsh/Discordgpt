
from src.actions.types import ActionDefinition


class ActionRegistry:
    _actions: dict[str, ActionDefinition] = {}

    @classmethod
    def register(cls, action: ActionDefinition) -> None:
        if action.type in cls._actions:
            raise ValueError(f"Action '{action.type}' is already registered.")
        cls._actions[action.type] = action

    @classmethod
    def get(cls, action_type: str) -> ActionDefinition | None:
        return cls._actions.get(action_type)

    @classmethod
    def get_all(cls) -> list[ActionDefinition]:
        return list(cls._actions.values())

    @classmethod
    def is_registered(cls, action_type: str) -> bool:
        return action_type in cls._actions
