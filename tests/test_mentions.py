"""Phase A: mention extraction, normalization, and slot auto-fill."""

from types import SimpleNamespace

from src.entities.mentions import (
    MentionSets,
    fill_from_pronouns,
    fill_slots_from_mentions,
    normalize_mentions,
    parse_mentions,
)


def _guild():
    channels = {
        111111111111111111: SimpleNamespace(id=111111111111111111, name="lobby"),
        222222222222222222: SimpleNamespace(id=222222222222222222, name="general"),
    }
    roles = {333333333333333333: SimpleNamespace(id=333333333333333333, name="Mods")}
    return SimpleNamespace(
        get_channel=lambda i: channels.get(i),
        get_role=lambda i: roles.get(i),
    )


def test_parse_all_mention_kinds():
    m = parse_mentions(
        "ban <@123456789012345678> in <#111111111111111111> else <@&333333333333333333>"
    )
    assert m.users == ["123456789012345678"]
    assert m.channels == ["111111111111111111"]
    assert m.roles == ["333333333333333333"]
    assert m.emojis == []
    assert not m.empty


def test_parse_nick_mention_and_emoji():
    m = parse_mentions("hi <@!123456789012345678> <:party:444444444444444444>")
    assert m.users == ["123456789012345678"]
    assert m.emojis == [("party", "444444444444444444")]


def test_parse_dedupes_and_ignores_short_ids():
    m = parse_mentions("<@123456789012345678> again <@123456789012345678> and <@123>")
    assert m.users == ["123456789012345678"]


def test_parse_empty():
    assert parse_mentions("just words").empty
    assert parse_mentions("").empty


def test_normalize_channel_and_role():
    out = normalize_mentions("lock <#111111111111111111> and give <@&333333333333333333>", _guild())
    assert out == "lock #lobby and give @Mods"


def test_normalize_keeps_user_mentions_and_unknown_ids():
    out = normalize_mentions("ban <@123456789012345678> in <#999999999999999999>", _guild())
    assert "<@123456789012345678>" in out
    assert "<#999999999999999999>" in out  # unknown ID preserved for slot-fill


def test_fill_member_slot_single_mention():
    params, filled = fill_slots_from_mentions(
        "ban_member", {}, MentionSets(users=["123456789012345678"])
    )
    assert params["member_id"] == "123456789012345678"
    assert filled == {"member_id": "<@123456789012345678>"}


def test_fill_refuses_multiple_mentions():
    params, filled = fill_slots_from_mentions(
        "kick_member", {}, MentionSets(users=["1" * 18, "2" * 18])
    )
    assert "member_id" not in params and filled == {}


def test_fill_does_not_override_explicit_params():
    params, filled = fill_slots_from_mentions(
        "ban_member",
        {"member_id": "9" * 18},
        MentionSets(users=["1" * 18], channels=["2" * 18]),
    )
    assert params["member_id"] == "9" * 18 and filled == {}


def test_fill_channel_only_for_channel_actions():
    params, filled = fill_slots_from_mentions("lock_channel", {}, MentionSets(channels=["2" * 18]))
    assert params["channel_id"] == "2" * 18
    assert filled == {"channel_id": f"<#{'2' * 18}>"}
    # ban_member takes no channel: a channel mention must not leak in.
    params, _ = fill_slots_from_mentions("ban_member", {}, MentionSets(channels=["2" * 18]))
    assert "channel_id" not in params


def test_fill_assign_role_pair():
    params, filled = fill_slots_from_mentions(
        "assign_role", {}, MentionSets(users=["1" * 18], roles=["3" * 18])
    )
    assert params == {"member_id": "1" * 18, "role_id": "3" * 18}
    assert filled == {"member_id": f"<@{'1' * 18}>", "role_id": f"<@&{'3' * 18}>"}


def test_fill_role_mutation_target():
    params, _filled = fill_slots_from_mentions("delete_role", {}, MentionSets(roles=["3" * 18]))
    assert params["role_id"] == "3" * 18


def test_pronoun_fills_from_recent_mention():
    history = ["user: look at <@123456789012345678>", "assistant: I see them."]
    params, filled = fill_from_pronouns("ban_member", {}, "ban him now", history)
    assert params["member_id"] == "123456789012345678"
    assert filled == {"member_id": "<@123456789012345678>"}


def test_pronoun_skipped_without_pronoun_or_history():
    params, filled = fill_from_pronouns("ban_member", {}, "ban the spammer", [])
    assert params == {} and filled == {}
    # Current-turn mention already filled: pronoun pass is a no-op.
    params, _ = fill_slots_from_mentions(
        "kick_member", {}, MentionSets(users=["123456789012345678"])
    )
    params, filled = fill_from_pronouns("kick_member", params, "kick him", [])
    assert filled == {}


def test_pronoun_needs_single_candidate():
    history = ["user: <@111111111111111111> and <@222222222222222222> spammed"]
    params, filled = fill_from_pronouns("ban_member", {}, "ban them", history)
    assert params == {} and filled == {}
