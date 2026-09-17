# Discord Agent Tool Catalog

Whitelisted Discord tools available through native Needle tool-calling and the deterministic execution dispatcher. Schemas: `tools/discord_tools.json` (generated via `export_tools_json`). Needle synthetics (`ask_clarification`, `chat_reply`) are planner-only and never dispatched.

## Core (original 23 + edit_channel)

| Tool Name | Description | Arguments & Constraints | Permissions Required | Risk Level | Confirmation | discord.py Method |
|---|---|---|---|---|---|---|
| `create_channel` | Creates a new text, voice, category, or forum channel. | `name` (str, max 100), `type` (text/voice/category/forum), `category_id` (opt), `topic` (max 1024) | `manage_channels` | LOW | NOT_REQUIRED | `guild.create_channel()` |
| `delete_channel` | Deletes a channel from the server. | `channel_id`, `reason` (opt) | `manage_channels` | HIGH | REQUIRED | `channel.delete()` |
| `edit_channel` | Edits channel properties (name, topic, nsfw). | `channel_id`, `name`/`topic`/`nsfw` (opt) | `manage_channels` | MEDIUM | NOT_REQUIRED | `channel.edit()` |
| `rename_channel` | Renames a channel. | `channel_id`, `new_name` (1-100) | `manage_channels` | LOW | NOT_REQUIRED | `channel.edit(name=)` |
| `set_topic` | Sets a text channel topic (empty clears it). | `channel_id`, `topic` (max 1024, opt) | `manage_channels` | LOW | NOT_REQUIRED | `channel.edit(topic=)` |
| `set_slowmode` | Sets slowmode delay in seconds (0 disables). | `channel_id`, `seconds` (0-21600) | `manage_channels` | LOW | NOT_REQUIRED | `channel.edit(slowmode_delay=)` |
| `lock_channel` | Denies Send Messages for @everyone. | `channel_id`, `reason` (opt) | `manage_channels`+`manage_roles` | MEDIUM | NOT_REQUIRED | `channel.set_permissions()` |
| `unlock_channel` | Resets @everyone Send Messages overwrite to neutral. | `channel_id`, `reason` (opt) | `manage_channels`+`manage_roles` | LOW | NOT_REQUIRED | `channel.set_permissions()` |
| `create_role` | Creates a new role. | `name` (max 100), `color`, `hoist`, `mentionable` | `manage_roles` | MEDIUM | NOT_REQUIRED | `guild.create_role()` |
| `assign_role` | Assigns a role to a member. | `member_id`, `role_id` | `manage_roles` | MEDIUM | NOT_REQUIRED | `member.add_roles()` |
| `delete_role` | Deletes a role. | `role_id`, `reason` (opt) | `manage_roles` | HIGH | REQUIRED | `role.delete()` |
| `remove_role` | Removes a role from a member. | `member_id`, `role_id` | `manage_roles` | MEDIUM | NOT_REQUIRED | `member.remove_roles()` |
| `edit_role` | Edits role name/color/hoist/mentionable. | `role_id` + at least one field | `manage_roles` | LOW | NOT_REQUIRED | `role.edit()` |
| `timeout_member` | Times out a member. | `member_id`, `duration_seconds` (1-2419200) | `moderate_members` | MEDIUM | REQUIRED | `member.timeout()` |
| `untimeout_member` | Removes an active timeout. | `member_id` | `moderate_members` | LOW | NOT_REQUIRED | `member.timeout(None)` |
| `kick_member` | Kicks a member (can rejoin). | `member_id`, `reason` (opt, 512) | `kick_members` | HIGH | REQUIRED | `member.kick()` |
| `ban_member` | Bans a member. | `member_id`, `reason`, `delete_message_seconds` (0-604800) | `ban_members` | HIGH | REQUIRED | `guild.ban()` |
| `unban_member` | Unbans a user by ID. | `user_id` | `ban_members` | MEDIUM | NOT_REQUIRED | `guild.unban()` |
| `set_nickname` | Sets/clears a member nickname. | `member_id`, `nickname` (max 32, opt) | `manage_nicknames` | LOW | NOT_REQUIRED | `member.edit(nick=)` |
| `move_member` | Moves/disconnects a voice member. | `member_id`, `channel_id` (opt) | `move_members` | LOW | NOT_REQUIRED | `member.move_to()` |
| `send_message` | Sends a message to a text channel. | `channel_id`, `content` (1-2000) | `send_messages` | LOW | NOT_REQUIRED | `channel.send()` |
| `edit_message` | Edits a bot-sent message. | `channel_id`, `message_id`, `content` | `send_messages` | LOW | NOT_REQUIRED | `message.edit()` |
| `delete_message` | Deletes a single message. | `channel_id`, `message_id` | `manage_messages` | MEDIUM | NOT_REQUIRED | `message.delete()` |
| `pin_message` | Pins a message. | `channel_id`, `message_id` | `manage_messages` | LOW | NOT_REQUIRED | `message.pin()` |
| `unpin_message` | Unpins a message. | `channel_id`, `message_id` | `manage_messages` | LOW | NOT_REQUIRED | `message.unpin()` |
| `purge_messages` | Bulk-deletes recent messages (max 100, skips pinned). | `channel_id`, `limit` (1-100), `user_id` (opt) | `manage_messages` | HIGH | REQUIRED | `channel.purge()` |

## Advanced (v2 coverage)

| Tool Name | Description | Arguments & Constraints | Permissions Required | Risk Level | Confirmation | discord.py Method |
|---|---|---|---|---|---|---|
| `create_thread` | Creates a thread, optionally on a message. | `channel_id`, `name` (1-100), `message_id` (opt), `auto_archive_minutes` (60-10080) | `send_messages`+`create_public_threads` | LOW | NOT_REQUIRED | `channel.create_thread()` / `message.create_thread()` |
| `add_reaction` | Adds an emoji reaction. | `channel_id`, `message_id`, `emoji` | `add_reactions` | LOW | NOT_REQUIRED | `message.add_reaction()` |
| `create_invite` | Creates a channel invite. | `channel_id`, `max_age` (0-604800), `max_uses` (0-100) | `create_instant_invite` | LOW | NOT_REQUIRED | `channel.create_invite()` |
| `mute_member` | Server-mutes/unmutes in voice. | `member_id`, `muted` (bool) | `mute_members` | LOW | NOT_REQUIRED | `member.edit(mute=)` |
| `deafen_member` | Server-deafens/undeafens in voice. | `member_id`, `deafened` (bool) | `deafen_members` | LOW | NOT_REQUIRED | `member.edit(deafen=)` |

## Planned (not yet implemented)

Scheduled events (`create_event`/`edit_event`/`delete_event`), emoji/sticker CRUD, webhooks (`create_webhook`/`send_via_webhook`), `schedule_action`/`cancel_schedule`, `save_command`/`run_saved_command`, audit lookup tool, polls (native `discord.Poll`).
