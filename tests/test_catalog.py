import src.actions.audit
import src.actions.automod
import src.actions.botself
import src.actions.channels
import src.actions.emojis
import src.actions.events
import src.actions.forum
import src.actions.guild
import src.actions.invites
import src.actions.members
import src.actions.messages
import src.actions.roles
import src.actions.schedules
import src.actions.soundboard
import src.actions.stage
import src.actions.stickers
import src.actions.system
import src.actions.threads
import src.actions.webhooks  # noqa: F401
from src.actions.plan_executor import summarize_plan
from src.actions.registry import ActionRegistry

EXPECTED = {
    "create_automod_rule", "edit_automod_rule", "get_audit_log", "prune_members",
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
    "delete_channel_permission",
    "create_role",
    "assign_role",
    "delete_role",
    "remove_role",
    "edit_role",
    "reorder_role",
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
    "join_thread", "leave_thread", "list_archived_threads",
    "archive_thread",
    "list_active_threads",
    "create_forum_post", "list_forum_tags", "set_forum_tags",
    "add_thread_member", "remove_thread_member",
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
    "edit_scheduled_event", "list_scheduled_event_users",
    "list_automod_rules",
    "create_keyword_rule",
    "delete_automod_rule",
    "create_webhook",
    "list_webhooks",
    "delete_webhook",
    "edit_webhook", "execute_webhook",
    "list_emojis",
    "create_emoji",
    "delete_emoji",
    "edit_emoji",
    "list_stickers", "create_sticker", "delete_sticker",
    "start_stage", "edit_stage", "end_stage",
    "list_soundboard_sounds", "create_soundboard_sound", "delete_soundboard_sound", "send_soundboard_sound",
    "get_welcome_screen", "edit_welcome_screen", "get_onboarding", "edit_onboarding",
    "get_widget", "edit_widget", "get_vanity_url", "list_integrations",
    "list_templates", "create_template", "sync_template", "delete_template", "set_bot_presence",
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
