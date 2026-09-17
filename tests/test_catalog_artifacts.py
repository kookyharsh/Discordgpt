"""Phase 1: catalog fingerprint + artifact refresh (isolated to tmp dirs)."""

import json

import src.actions.automod
import src.actions.channels
import src.actions.emojis
import src.actions.events
import src.actions.guild
import src.actions.invites
import src.actions.members
import src.actions.messages
import src.actions.roles
import src.actions.schedules
import src.actions.system
import src.actions.threads
import src.actions.webhooks  # noqa: F401  (populate registry)
import src.ai.needle_agent as na
from src.actions.registry import ActionRegistry


def _isolate(monkeypatch, tmp_path):
    tools_dir = tmp_path / "tools"
    monkeypatch.setattr(na, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(na, "CATALOG_JSON", str(tools_dir / "discord_tools.json"))
    monkeypatch.setattr(na, "CATALOG_HASH_FILE", tools_dir / ".catalog_hash")
    return tools_dir


def test_fingerprint_stable_and_sensitive():
    fp1 = na.catalog_fingerprint()
    fp2 = na.catalog_fingerprint()
    assert fp1 == fp2 and len(fp1) == 12
    first = min(ActionRegistry.get_all(), key=lambda a: a.type)
    original = first.description
    try:
        first.description = original + " extra words"
        assert na.catalog_fingerprint() != fp1
    finally:
        first.description = original
    assert na.catalog_fingerprint() == fp1


def test_refresh_writes_once_then_noops(monkeypatch, tmp_path):
    tools_dir = _isolate(monkeypatch, tmp_path)
    info = na.refresh_artifacts()
    assert info["changed"] is True
    catalog = json.loads((tools_dir / "discord_tools.json").read_text())
    names = {t["name"] for t in catalog}
    assert "schedule_action" in names and "create_channel" in names
    assert len(catalog) == len(ActionRegistry.get_all())
    info2 = na.refresh_artifacts()
    assert info2["changed"] is False
    assert info2["fingerprint"] == info["fingerprint"]


def test_resolve_index_path_embeds_fingerprint(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    path = na.resolve_index_path()
    assert path.endswith(f"tools.{na.catalog_fingerprint()}.idx")
    monkeypatch.setenv("NEEDLE_TOOL_INDEX", "/override/custom.idx")
    try:
        assert na.resolve_index_path() == "/override/custom.idx"
    finally:
        monkeypatch.delenv("NEEDLE_TOOL_INDEX", raising=False)


def test_check_artifacts_stale_logs_on_change(monkeypatch, tmp_path, caplog):
    _isolate(monkeypatch, tmp_path)
    import logging

    with caplog.at_level(logging.INFO, logger="discord_agent.needle"):
        na.check_artifacts_stale()
    assert any("indexed" in r.message for r in caplog.records)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="discord_agent.needle"):
        na.check_artifacts_stale()
    assert not caplog.records
