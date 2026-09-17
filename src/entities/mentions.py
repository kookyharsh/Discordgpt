"""Discord mention syntax handling.

Discord delivers mentions as raw syntax inside the `/prompt` string:
`<@id>`/`<@!id>` users, `<#id>` channels, `<@&id>` roles, `<:name:id>` emoji.
This module extracts them (so IDs are never lost) and normalizes channel /
role mentions to `#name` / `@name` for the text parsers, which speak names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

USER_MENTION_RE = re.compile(r"<@!?(\d{15,25})>")
CHANNEL_MENTION_RE = re.compile(r"<#(\d{15,25})>")
ROLE_MENTION_RE = re.compile(r"<@&(\d{15,25})>")
EMOJI_MENTION_RE = re.compile(r"<a?:([A-Za-z0-9_~]+):(\d{15,25})>")

PRONOUN_MEMBER_RE = re.compile(r"\b(him|her|them|they|he|she)\b", re.IGNORECASE)
PRONOUN_CHANNEL_RE = re.compile(r"\b(there|that channel|this channel)\b", re.IGNORECASE)


@dataclass
class MentionSets:
    users: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    emojis: list[tuple[str, str]] = field(default_factory=list)  # (name, id)

    @property
    def empty(self) -> bool:
        return not (self.users or self.channels or self.roles or self.emojis)


def _unique(ids: list[str]) -> list[str]:
    seen: list[str] = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    return seen


def parse_mentions(text: str) -> MentionSets:
    """Extract all mention IDs from raw Discord message text."""
    return MentionSets(
        users=_unique(USER_MENTION_RE.findall(text or "")),
        channels=_unique(CHANNEL_MENTION_RE.findall(text or "")),
        roles=_unique(ROLE_MENTION_RE.findall(text or "")),
        emojis=[(m.group(1), m.group(2)) for m in EMOJI_MENTION_RE.finditer(text or "")],
    )


def normalize_mentions(text: str, guild) -> str:
    """Rewrite `<#id>` -> `#name` and `<@&id>` -> `@name` for text parsers.

    User mentions are left intact (fallback regexes speak `<@id>`).
    Unknown IDs are left as-is so the mention sets can still use them.
    """
    if not text or guild is None:
        return text

    def _channel_name(match: re.Match) -> str:
        try:
            ch = guild.get_channel(int(match.group(1)))
        except (TypeError, ValueError):
            return match.group(0)
        name = getattr(ch, "name", None)
        return f"#{name}" if name else match.group(0)

    def _role_name(match: re.Match) -> str:
        try:
            role = guild.get_role(int(match.group(1)))
        except (TypeError, ValueError):
            return match.group(0)
        name = getattr(role, "name", None)
        return f"@{name}" if name else match.group(0)

    text = CHANNEL_MENTION_RE.sub(_channel_name, text)
    return ROLE_MENTION_RE.sub(_role_name, text)


MEMBER_TARGET_ACTIONS = frozenset(
    {
        "timeout_member",
        "untimeout_member",
        "kick_member",
        "ban_member",
        "set_nickname",
        "move_member",
        "mute_member",
        "deafen_member",
    }
)
USER_ID_ACTIONS = frozenset({"unban_member"})


def _take_single(ids: list[str]) -> str | None:
    return ids[0] if len(ids) == 1 else None


def _member_slot(action: str) -> str | None:
    if action in MEMBER_TARGET_ACTIONS or action in ("assign_role", "remove_role"):
        return "member_id"
    if action in USER_ID_ACTIONS:
        return "user_id"
    return None


def fill_from_pronouns(
    action: str, params: dict, prompt: str, history_lines: list[str] | None
) -> tuple[dict, dict[str, str]]:
    """Resolve him/her/them to the most recently mentioned user.

    Scans current-turn mentions first (handled by fill_slots_from_mentions),
    then prior user turns. Only fills when the prompt actually contains a
    member pronoun and exactly one candidate exists.
    """
    params = dict(params)
    filled: dict[str, str] = {}
    slot = _member_slot(action)
    if not slot or params.get(slot) or not PRONOUN_MEMBER_RE.search(prompt or ""):
        return params, filled
    for line in reversed(history_lines or []):
        if not str(line).lower().startswith("user:"):
            continue
        users = parse_mentions(str(line)).users
        if len(users) == 1:
            params[slot] = users[0]
            filled[slot] = f"<@{users[0]}>"
            return params, filled
    return params, filled


def fill_slots_from_mentions(
    action: str, params: dict, mentions: MentionSets
) -> tuple[dict, dict[str, str]]:
    """Auto-fill empty target slots from message mentions.

    Only fills when exactly one mention of the matching kind exists, so
    `send hello to #general @Bob` never mistakes Bob for the target.
    Returns (params, filled) where filled maps slot -> mention markdown
    (`<@id>` / `<#id>`) for announcement in the reply.
    """
    params = dict(params)
    filled: dict[str, str] = {}

    if action in MEMBER_TARGET_ACTIONS and not params.get("member_id"):
        uid = _take_single(mentions.users)
        if uid:
            params["member_id"] = uid
            filled["member_id"] = f"<@{uid}>"
    elif action in USER_ID_ACTIONS and not params.get("user_id"):
        uid = _take_single(mentions.users)
        if uid:
            params["user_id"] = uid
            filled["user_id"] = f"<@{uid}>"
    elif action in ("assign_role", "remove_role"):
        if not params.get("member_id"):
            uid = _take_single(mentions.users)
            if uid:
                params["member_id"] = uid
                filled["member_id"] = f"<@{uid}>"
        if not params.get("role_id"):
            rid = _take_single(mentions.roles)
            if rid:
                params["role_id"] = rid
                filled["role_id"] = f"<@&{rid}>"

    if not params.get("channel_id") and not params.get("channel_name"):
        cid = _take_single(mentions.channels)
        if cid and _action_takes_channel(action):
            params["channel_id"] = cid
            filled["channel_id"] = f"<#{cid}>"

    if not params.get("role_id") and not params.get("role_name"):
        rid = _take_single(mentions.roles)
        if rid and action in ("create_role", "edit_role", "delete_role"):
            # Role mention on a role-mutation action names its target.
            params["role_id"] = rid
            filled["role_id"] = f"<@&{rid}>"

    return params, filled


def _action_takes_channel(action: str) -> bool:
    return action in {
        "send_message",
        "purge_messages",
        "set_slowmode",
        "lock_channel",
        "unlock_channel",
        "rename_channel",
        "set_topic",
        "pin_message",
        "unpin_message",
        "delete_channel",
        "edit_channel",
        "move_channel",
        "set_channel_permissions",
        "create_thread",
        "add_reaction",
        "create_invite",
        "create_webhook",
        "edit_message",
        "delete_message",
        "fetch_history",
        "clear_reactions",
    }
