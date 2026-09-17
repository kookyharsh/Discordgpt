from __future__ import annotations

import re
from typing import Any, ClassVar


class FallbackParser:
    """Offline regex pre-filter. Mirrors the TS FallbackParser intent coverage.

    Emits {"action": str, "parameters": dict} with *name-based* keys
    (channel_name/role_name) where resolution is still needed, and
    *id-based* keys (member_id/role_id/channel_id) for mentions.
    Returns None on miss so Needle can take over.

    Scheduling: "make a channel in 10 seconds" / "every day at 9am, send ..."
    emits {"status": "schedule_request", "action": ..., "parameters": ...,
    "delay_seconds": N} or {"cron": "...", "schedule_human": "..."}.
    """

    _WEEKDAYS: ClassVar[dict[str, int]] = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 0,
    }

    @staticmethod
    def _parse_time(hour: str, minute: str | None, meridiem: str | None) -> tuple[int, int] | None:
        h, m = int(hour), int(minute or 0)
        mer = (meridiem or "").lower()
        if mer == "pm" and h < 12:
            h += 12
        if mer == "am" and h == 12:
            h = 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return h, m

    @staticmethod
    def extract_schedule(prompt: str) -> tuple[dict[str, Any] | None, str]:
        """Detect a delay/cron clause. Returns (spec, cleaned_prompt).

        spec is None when no scheduling language is found, else e.g.
        {"delay_seconds": 10, "schedule_human": "in 10 seconds"} or
        {"cron": "30 9 * * *", "schedule_human": "every day at 9:30 AM"}.
        """
        raw = prompt.strip()

        m = re.search(
            r"\b(?:in|after)\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d)\b",
            raw,
            re.IGNORECASE,
        )
        if m:
            amount = int(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith("s"):
                delay = amount
            elif unit.startswith("m"):
                # bare "m" could be ambiguous, but in an in/after clause it means minutes
                delay = amount * 60
            elif unit.startswith("h"):
                delay = amount * 3600
            else:
                delay = amount * 86400
            cleaned = (raw[: m.start()] + raw[m.end() :]).strip(" ,.")
            return {"delay_seconds": delay, "schedule_human": m.group(0)}, cleaned or raw

        m = re.search(
            r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
            r"\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
            raw,
            re.IGNORECASE,
        )
        if m:
            parsed = FallbackParser._parse_time(m.group(2), m.group(3), m.group(4))
            if parsed:
                h, mi = parsed
                dow = FallbackParser._WEEKDAYS[m.group(1).lower()]
                cleaned = (raw[: m.start()] + raw[m.end() :]).strip(" ,.")
                return {
                    "cron": f"{mi} {h} * * {dow}",
                    "schedule_human": m.group(0),
                }, cleaned or raw

        m = re.search(
            r"\bevery\s+day\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", raw, re.IGNORECASE
        )
        if m:
            parsed = FallbackParser._parse_time(m.group(1), m.group(2), m.group(3))
            if parsed:
                h, mi = parsed
                cleaned = (raw[: m.start()] + raw[m.end() :]).strip(" ,.")
                return {
                    "cron": f"{mi} {h} * * *",
                    "schedule_human": m.group(0),
                }, cleaned or raw

        m = re.search(r"\bevery\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\b", raw, re.IGNORECASE)
        if m:
            amount = int(m.group(1))
            if m.group(2).lower().startswith("m"):
                if amount < 1 or amount > 59 or 60 % amount != 0:
                    return None, raw
                cron = f"*/{amount} * * * *"
            else:
                if amount < 1 or amount > 24 or 24 % amount != 0:
                    return None, raw
                cron = f"0 */{amount} * * *"
            cleaned = (raw[: m.start()] + raw[m.end() :]).strip(" ,.")
            return {"cron": cron, "schedule_human": m.group(0)}, cleaned or raw

        m = re.search(r"\bevery\s+hour\b", raw, re.IGNORECASE)
        if m:
            cleaned = (raw[: m.start()] + raw[m.end() :]).strip(" ,.")
            return {"cron": "0 * * * *", "schedule_human": m.group(0)}, cleaned or raw

        return None, raw

    @staticmethod
    def parse(prompt: str) -> dict[str, Any] | None:
        sched, cleaned = FallbackParser.extract_schedule(prompt)
        inner = FallbackParser._parse_direct(cleaned)
        if sched is not None:
            if inner is None:
                # Scheduling language found but the inner action isn't one the
                # offline parser knows - let Needle try (the handler re-checks
                # the schedule clause for Needle results too).
                return None
            return {"status": "schedule_request", **sched, **inner}
        return inner

    @staticmethod
    def _parse_direct(prompt: str) -> dict[str, Any] | None:
        normalized = prompt.strip().lower()
        raw = prompt.strip()

        m = re.search(
            r"create (?:a )?(?:text )?channel (?:called |named )?([a-z0-9-_]+)",
            normalized,
            re.IGNORECASE,
        )
        if m:
            return {"action": "create_channel", "parameters": {"name": m.group(1), "type": "text"}}

        m = re.search(
            r"(?:delete|remove) (?:the )?(?:text )?channel (?:called |named )?#?([a-z0-9-_]+)",
            normalized,
            re.IGNORECASE,
        )
        if m:
            return {"action": "delete_channel", "parameters": {"channel_name": m.group(1)}}

        m = re.search(
            r"create (?:a )?role (?:called |named )?([a-z0-9-_ ]+?)\s*$", normalized, re.IGNORECASE
        )
        if m:
            return {"action": "create_role", "parameters": {"name": m.group(1).strip()}}

        # NOTE: untimeout/unban checks must precede timeout/ban ("untimeout" contains "timeout").
        m = re.search(r"\b(?:untimeout|unmute)\s+<@!?(\d{15,25})>", raw, re.IGNORECASE)
        if m:
            return {"action": "untimeout_member", "parameters": {"member_id": m.group(1)}}

        m = re.search(
            r"(?<!un)\btimeout\s+<@!?(\d{15,25})>(?:\s+for\s+(\d+)\s*(s(?:ec(?:ond)?s?)?|m(?:in(?:ute)?s?)?)?)?",
            raw,
            re.IGNORECASE,
        )
        if m:
            amount = int(m.group(2)) if m.group(2) else 300
            unit = (m.group(3) or "s").lower()
            return {
                "action": "timeout_member",
                "parameters": {
                    "member_id": m.group(1),
                    "duration_seconds": amount * 60 if unit.startswith("m") else amount,
                },
            }

        m = re.search(r"(?<!un)\bban\s+<@!?(\d{15,25})>(?:\s+(?:for\s+)?(.+))?", raw, re.IGNORECASE)
        if m:
            params: dict[str, Any] = {"member_id": m.group(1)}
            if m.group(2):
                params["reason"] = m.group(2).strip()[:512]
            return {"action": "ban_member", "parameters": params}

        m = re.search(
            r"<@!?(\d{15,25})>[\s\S]*?<@&(\d{15,25})>|<@&(\d{15,25})>[\s\S]*?<@!?(\d{15,25})>", raw
        )
        if m:
            member_id = m.group(1) or m.group(4)
            role_id = m.group(2) or m.group(3)
            if member_id and role_id:
                return {
                    "action": "assign_role",
                    "parameters": {"member_id": member_id, "role_id": role_id},
                }

        m = re.search(r"\bkick\s+<@!?(\d{15,25})>(?:\s+(?:for\s+)?(.+))?", raw, re.IGNORECASE)
        if m:
            params = {"member_id": m.group(1)}
            if m.group(2):
                params["reason"] = m.group(2).strip()[:512]
            return {"action": "kick_member", "parameters": params}

        m = re.search(r"\bunban\s+(?:<@!?(\d{15,25})>|(\d{15,25}))", normalized)
        if m:
            return {"action": "unban_member", "parameters": {"user_id": m.group(1) or m.group(2)}}

        m = re.search(r"\bnick(?:name)?\s+<@!?(\d{15,25})>\s+(.+?)\s*$", raw, re.IGNORECASE)
        if m:
            name = m.group(2).strip()
            params = {"member_id": m.group(1)}
            if not re.match(r"^(clear|reset|remove)$", name, re.IGNORECASE):
                params["nickname"] = name[:32]
            return {"action": "set_nickname", "parameters": params}

        m = re.search(r"\bslow ?mode\s+(off|disable|0|\d+)\b", normalized, re.IGNORECASE)
        if m:
            seconds = min(int(m.group(1)), 21600) if re.match(r"^\d+$", m.group(1)) else 0
            chan = re.search(r"(?:in|for)\s+#?([a-z0-9-_]+)", normalized)
            params = {"seconds": seconds}
            if chan:
                params["channel_name"] = chan.group(1)
            return {"action": "set_slowmode", "parameters": params}

        m = re.search(r"\bunlock\b(?:\s+channel)?\s*#?([a-z0-9-_]+)?", normalized)
        if m:
            params = {}
            if m.group(1):
                params["channel_name"] = m.group(1)
            return {"action": "unlock_channel", "parameters": params}

        m = re.search(r"\block\b(?:\s+channel)?\s*#?([a-z0-9-_]+)?", normalized)
        if m:
            params = {}
            if m.group(1):
                params["channel_name"] = m.group(1)
            return {"action": "lock_channel", "parameters": params}

        m = re.search(
            r"\brename\s+(?:channel\s+)?#?([a-z0-9-_]+)\s+to\s+([a-z0-9-_ ]+?)\s*$",
            normalized,
            re.IGNORECASE,
        )
        if m:
            return {
                "action": "rename_channel",
                "parameters": {"channel_name": m.group(1), "new_name": m.group(2).strip()},
            }

        m = re.search(
            r"\b(purge|clear|delete)\s+(\d{1,3})(?:\s+messages?)?(?:\s+(?:in|from)\s+#?([a-z0-9-_]+))?",
            normalized,
        )
        if m:
            verb = m.group(1)
            has_target = bool(re.search(r"messages?", normalized)) or bool(m.group(3))
            # Bare "delete 5" is ambiguous (channel? role?) - leave it to Needle.
            if verb != "delete" or has_target:
                params = {"limit": min(int(m.group(2)), 100)}
                if m.group(3):
                    params["channel_name"] = m.group(3)
                return {"action": "purge_messages", "parameters": params}

        m = re.search(
            r'send (?:message )?"([^"]+)" to <#?([a-z0-9-_]+)>?', normalized, re.IGNORECASE
        )
        if m:
            return {
                "action": "send_message",
                "parameters": {"content": m.group(1), "channel_name": m.group(2)},
            }

        return None
