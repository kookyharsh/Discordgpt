# Discord Agent Tool Catalog

The table below documents all whitelisted Discord tools made available through Needle tool-calling and the deterministic execution dispatcher.

| Tool Name | Description | Arguments & Constraints | Permissions Required | Risk Level | Confirmation Policy | discord.py Method |
|---|---|---|---|---|---|---|
| `create_channel` | Creates a new text, voice, category, or forum channel. | `name` (str, max 100), `type` ("text", "voice", "category", "forum"), `category_id` (str, optional), `topic` (str, max 1024) | `manage_channels` | LOW | NOT_REQUIRED | `guild.create_channel()` |
| `delete_channel` | Deletes a channel from the server. | `channel_id` (str), `reason` (str, optional) | `manage_channels` | HIGH | REQUIRED | `channel.delete()` |
| `edit_channel` | Edits channel properties (name, topic, nsfw). | `channel_id` (str), `name` (str, max 100), `topic` (str, max 1024), `nsfw` (bool) | `manage_channels` | MEDIUM | NOT_REQUIRED | `channel.edit()` |
| `create_role` | Creates a new role in the server. | `name` (str, max 100), `color` (hex str), `hoist` (bool), `mentionable` (bool) | `manage_roles` | MEDIUM | NOT_REQUIRED | `guild.create_role()` |
| `assign_role` | Assigns a role to a server member. | `member_id` (str), `role_id` (str) | `manage_roles` | MEDIUM | NOT_REQUIRED | `member.add_roles()` |
| `timeout_member` | Times out a member for a specified duration in seconds. | `member_id` (str), `duration_seconds` (int, 1..2419200), `reason` (str) | `moderate_members` | MEDIUM | REQUIRED | `member.timeout()` |
| `ban_member` | Bans a member from the guild. | `member_id` (str), `reason` (str), `delete_message_seconds` (int, 0..604800) | `ban_members` | HIGH | REQUIRED | `guild.ban()` |
| `send_message` | Sends a message to a text channel. | `channel_id` (str), `content` (str, max 2000) | `send_messages` | LOW | NOT_REQUIRED | `channel.send()` |
| `ask_clarification` | Synthetic tool to ask user clarifying questions when parameters are missing. | `question` (str) | None | LOW | NOT_REQUIRED | None (Synthetic) |
| `chat_reply` | Synthetic tool to respond conversationally to non-action requests. | `message` (str) | None | LOW | NOT_REQUIRED | None (Synthetic) |
