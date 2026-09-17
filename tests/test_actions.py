import src.actions.channels
import src.actions.members
import src.actions.messages
import src.actions.roles
import src.actions.schedules  # noqa: F401
from src.actions.registry import ActionRegistry


def test_action_registry():
    assert ActionRegistry.is_registered("create_channel") is True
    assert ActionRegistry.is_registered("delete_channel") is True
    assert ActionRegistry.is_registered("timeout_member") is True
    assert ActionRegistry.is_registered("arbitrary_code_execution") is False
