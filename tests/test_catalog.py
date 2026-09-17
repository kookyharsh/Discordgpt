import src.actions.automod
import src.actions.channels
import src.actions.emojis
import src.actions.events
import src.actions.guild
import src.actions.invites
import src.actions.members
import src.actions.messages
import src.actions.roles
import src.actions.schedules
import src.actions.system
import src.actions.threads
import src.actions.webhooks  # noqa: F401
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
    "move_channel",
    "set_channel_permissions",
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
    "mute_member",
    "deafen_member",
    "send_message",
    "edit_message",
    "delete_message",
    "pin_message",
    "unpin_message",
    "purge_messages",
    "fetch_history",
    "clear_reactions",
    "create_thread",
    "archive_thread",
    "list_active_threads",
    "add_reaction",
    "create_invite",
    "list_invites",
    "delete_invite",
    "get_guild_info",
    "edit_guild",
    "list_bans",
    "create_scheduled_event",
    "list_scheduled_events",
    "delete_scheduled_event",
    "list_automod_rules",
    "create_keyword_rule",
    "delete_automod_rule",
    "create_webhook",
    "list_webhooks",
    "delete_webhook",
    "list_emojis",
    "create_emoji",
    "delete_emoji",
    "schedule_action",
    "list_schedules",
    "cancel_schedule",
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
