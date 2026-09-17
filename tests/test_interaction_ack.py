from types import SimpleNamespace

import pytest

from src.bot.interaction_handler import BotInteractionHandler


def _stub_interaction():
    calls = {"defer": 0, "followup": []}

    async def defer(*args, **kwargs):
        calls["defer"] += 1

    async def send(*args, **kwargs):
        calls["followup"].append((args, kwargs))

    return (
        SimpleNamespace(
            guild=None,
            response=SimpleNamespace(defer=defer),
            followup=SimpleNamespace(send=send),
        ),
        calls,
    )


@pytest.mark.asyncio
async def test_handle_prompt_defers_fresh_interaction():
    handler = BotInteractionHandler(bot=None)
    interaction, calls = _stub_interaction()
    await handler.handle_prompt(interaction, "hi")
    assert calls["defer"] == 1
    assert len(calls["followup"]) == 1


@pytest.mark.asyncio
async def test_handle_prompt_skips_defer_when_already_deferred():
    # Modal-submit resume path: exactly one initial response per interaction,
    # so a second defer would raise InteractionResponded.
    handler = BotInteractionHandler(bot=None)
    interaction, calls = _stub_interaction()
    await handler.handle_prompt(interaction, "hi", already_deferred=True)
    assert calls["defer"] == 0
    assert len(calls["followup"]) == 1
