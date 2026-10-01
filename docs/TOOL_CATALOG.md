# Discord Agent Tool Catalog

This catalog is generated from the live `ActionRegistry`. Needle receives the same schemas that `ActionDispatcher` validates. The generated JSON is at `tools/discord_tools.json`; run `refresh_artifacts()` after registry changes.

The bot currently exposes 102 whitelisted actions. Every action has a Pydantic schema, native `discord.py` handler, bot/user permissions, risk level, and confirmation policy.

## Capability groups

- Channels: text, announcement, voice, stage, category, forum, and media-capable channels; edit, move, lock, slowmode, topics, permission overwrites, and overwrite deletion.
- Messages: content, embeds, replies, HTTPS attachments, stickers, polls, reactions, history, pinning, editing, deletion, purge, and announcement publishing.
- Threads/forums: create, archive/unarchive, join/leave, member add/remove, active/archived listing, forum posts, and forum tag operations.
- Members/roles: timeout, kick, ban/unban, nickname, voice mute/deafen/move, role assignment/removal/editing, permission bits, deletion, and reordering.
- Guild administration: guild info/edit, bans, audit log, prune preview/execute, welcome screen, onboarding, widget, vanity lookup, integrations, and scheduled events/RSVPs.
- Templates and bot self-management: list/create/sync/delete server templates and set bot presence/activity.
- AutoMod: list, keyword/mention-spam/preset/member-profile creation, edit, and delete.
- Expressions: emoji list/create/edit/delete and sticker list/create/delete.
- Events and voice surfaces: stage lifecycle and soundboard sound management/effects. No voice playback or audio streaming is included.
- Webhooks/invites: create/list/edit/delete webhooks, confirmed webhook execution, and invite lifecycle.
- Schedules: DB-backed delayed and cron action execution.

## Safety boundary

Natural language never calls Discord directly. Unknown actions, arbitrary code, generic HTTP paths, OAuth user-token flows, Activities/Social SDKs, developer-portal settings, gateway event triggers, guild deletion, and music playback are not registered tools.

Destructive operations such as bans, channel/role/sticker/sound deletion, pruning, stage ending, webhook execution, and purges use high-risk confirmation where applicable. Tenant isolation, guild policy, Discord permissions, role hierarchy, and confirmation hashes are enforced by the dispatcher before handlers run.

## Complete live action names

`create_channel`, `delete_channel`, `edit_channel`, `rename_channel`, `set_topic`, `set_slowmode`, `lock_channel`, `unlock_channel`, `move_channel`, `set_channel_permissions`, `delete_channel_permission`, `create_role`, `assign_role`, `delete_role`, `remove_role`, `edit_role`, `reorder_role`, `timeout_member`, `untimeout_member`, `kick_member`, `ban_member`, `unban_member`, `set_nickname`, `move_member`, `mute_member`, `deafen_member`, `send_message`, `edit_message`, `delete_message`, `pin_message`, `unpin_message`, `purge_messages`, `fetch_history`, `add_reaction`, `remove_reaction`, `clear_reactions`, `create_poll`, `publish_message`, `create_thread`, `join_thread`, `leave_thread`, `archive_thread`, `list_active_threads`, `list_archived_threads`, `add_thread_member`, `remove_thread_member`, `create_forum_post`, `list_forum_tags`, `set_forum_tags`, `create_invite`, `list_invites`, `delete_invite`, `get_guild_info`, `edit_guild`, `list_bans`, `get_audit_log`, `prune_members`, `get_welcome_screen`, `edit_welcome_screen`, `get_onboarding`, `edit_onboarding`, `get_widget`, `edit_widget`, `get_vanity_url`, `list_integrations`, `create_scheduled_event`, `edit_scheduled_event`, `list_scheduled_events`, `list_scheduled_event_users`, `delete_scheduled_event`, `list_automod_rules`, `create_keyword_rule`, `create_automod_rule`, `edit_automod_rule`, `delete_automod_rule`, `create_webhook`, `edit_webhook`, `execute_webhook`, `list_webhooks`, `delete_webhook`, `list_emojis`, `create_emoji`, `edit_emoji`, `delete_emoji`, `list_stickers`, `create_sticker`, `delete_sticker`, `start_stage`, `edit_stage`, `end_stage`, `list_soundboard_sounds`, `create_soundboard_sound`, `delete_soundboard_sound`, `send_soundboard_sound`, `schedule_action`, `list_schedules`, `cancel_schedule`.
