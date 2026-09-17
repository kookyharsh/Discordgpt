"""Phase 1: compact guild context builder respects the token budget."""

from types import SimpleNamespace

from src.ai.context import MAX_SYSTEM_TOKENS, build_system, estimate_tokens


def _guild(n_channels=30, n_roles=12):
    channels = [SimpleNamespace(id=str(1000 + i), name=f"chan-{i}") for i in range(n_channels)]
    roles = [SimpleNamespace(id=str(2000 + i), name=f"Role {i}") for i in range(n_roles)]
    return SimpleNamespace(channels=channels, roles=roles, member_count=42)


def test_snapshot_contains_names_and_current_channel():
    guild = _guild()
    out = build_system(guild, current_channel_id="1005", history=[])
    assert "date:" in out and "locale: en-US" in out
    assert "#chan-5" in out  # current channel first
    assert "#chan-0" in out and "@Role 0" in out
    assert "members: 42" in out
    # Names, not snowflakes: the resolver maps names to IDs.
    assert "1000" not in out


def test_history_is_structured_and_truncated():
    guild = _guild(n_channels=2, n_roles=1)
    history = [f"user: {'x' * 200}", "assistant: ok", "user: do it again"]
    out = build_system(guild, history=history)
    assert "prev:" in out
    assert "x" * 200 not in out  # per-turn cap
    assert estimate_tokens(out) <= MAX_SYSTEM_TOKENS


def test_large_guild_stays_within_budget():
    big = SimpleNamespace(
        channels=[SimpleNamespace(id=str(i), name=f"channel-number-{i}") for i in range(200)],
        roles=[SimpleNamespace(id=str(i), name=f"Some Role {i}") for i in range(100)],
        member_count=5000,
    )
    history = [f"user: message number {i} " + "y" * 300 for i in range(10)]
    out = build_system(big, history=history)
    assert estimate_tokens(out) <= MAX_SYSTEM_TOKENS
    assert "date:" in out  # core facts survive truncation


def test_broken_guild_objects_do_not_crash():
    assert "date:" in build_system(None, history=None)
    assert "date:" in build_system(SimpleNamespace(), history=["user: hi"])
    out = build_system(_guild(), current_channel_id="nope", history=[])
    assert "here:" not in out


def test_old_builder_would_have_blown_the_window():
    # What the previous code fed the engine: 6x300-char history lines.
    history = [f"user: {'z' * 300}" for _ in range(6)]
    old = "; history: " + " | ".join(history)
    assert estimate_tokens(old) > MAX_SYSTEM_TOKENS
    new = build_system(_guild(), history=history)
    assert estimate_tokens(new) <= MAX_SYSTEM_TOKENS


def test_people_fact_maps_mentions():
    out = build_system(_guild(), history=[], people={"123456789012345678": "@Bob"})
    assert "people: @Bob=123456789012345678" in out
    assert estimate_tokens(out) <= MAX_SYSTEM_TOKENS
