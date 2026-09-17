import src.actions.advanced_tools
import src.actions.extra_tools
import src.actions.needle_tools  # noqa: F401
from src.actions.plan_executor import summarize_plan
from src.actions.registry import ActionRegistry

EXPECTED = {
    "create_channel",
    "delete_channel",
    "edit_channel",
    "rename_channel",
    "set_topic",
    "set_slowmode",
    "lock_channel",
    "unlock_channel",
    "create_role",
    "assign_role",
    "delete_role",
    "remove_role",
    "edit_role",
    "timeout_member",
    "untimeout_member",
    "kick_member",
    "ban_member",
    "unban_member",
    "set_nickname",
    "move_member",
    "send_message",
    "edit_message",
    "delete_message",
    "pin_message",
    "unpin_message",
    "purge_messages",
    "create_thread",
    "add_reaction",
    "create_invite",
    "mute_member",
    "deafen_member",
}


def test_full_catalog_registered():
    registered = {a.type for a in ActionRegistry.get_all()}
    assert EXPECTED <= registered, f"missing: {EXPECTED - registered}"


def test_every_tool_has_description_and_schema():
    for act in ActionRegistry.get_all():
        assert act.description and len(act.description) > 10
        schema = act.input_schema.model_json_schema()
        assert schema.get("type") == "object"
        assert isinstance(schema.get("properties", {}), dict)


def test_no_arbitrary_execution():
    assert not ActionRegistry.is_registered("arbitrary_code_execution")
    assert ActionRegistry.get("eval") is None


def test_summarize_plan():
    results = [
        {"action": "create_channel", "ok": True},
        {"action": "ban_member", "ok": False, "error": "missing perms"},
    ]
    summary = summarize_plan(results)
    assert "1/2" in summary and "✓ create_channel" in summary and "✗ ban_member" in summary
    assert summarize_plan([]) == "No steps were executed."
