from src.ai.fallback_parser import FallbackParser


def test_create_channel():
    r = FallbackParser.parse("create channel welcome")
    assert r == {"action": "create_channel", "parameters": {"name": "welcome", "type": "text"}}


def test_timeout_with_duration():
    r = FallbackParser.parse("timeout <@123456789012345678> for 10 m")
    assert r is not None
    assert r["action"] == "timeout_member"
    assert r["parameters"]["member_id"] == "123456789012345678"
    assert r["parameters"]["duration_seconds"] == 600


def test_untimeout_precedence():
    r = FallbackParser.parse("untimeout <@123456789012345678>")
    assert r is not None and r["action"] == "untimeout_member"


def test_ban_with_reason():
    r = FallbackParser.parse("ban <@123456789012345678> for spamming")
    assert r is not None and r["action"] == "ban_member"
    assert r["parameters"]["member_id"] == "123456789012345678"


def test_assign_role_mention_order_independent():
    r = FallbackParser.parse("give <@111111111111111111> the <@&222222222222222222> role")
    assert r == {
        "action": "assign_role",
        "parameters": {"member_id": "111111111111111111", "role_id": "222222222222222222"},
    }


def test_kick():
    r = FallbackParser.parse("kick <@123456789012345678>")
    assert r is not None and r["action"] == "kick_member"


def test_purge_with_channel():
    r = FallbackParser.parse("purge 20 messages in general")
    assert r is not None and r["action"] == "purge_messages"
    assert r["parameters"]["limit"] == 20


def test_bare_delete_number_is_ambiguous():
    assert FallbackParser.parse("delete 5") is None


def test_slowmode_off():
    r = FallbackParser.parse("slowmode off in general")
    assert r is not None and r["action"] == "set_slowmode"
    assert r["parameters"]["seconds"] == 0


def test_rename():
    r = FallbackParser.parse("rename channel general to lobby")
    assert r is not None and r["action"] == "rename_channel"


def test_miss_returns_none():
    assert FallbackParser.parse("what is the weather like?") is None
