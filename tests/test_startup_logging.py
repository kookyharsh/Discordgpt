import logging

from rich.console import Console
from rich.logging import RichHandler

from src.bot import logger as startup_logger


def _fresh_setup(monkeypatch, **env):
    startup_logger.reset_logging_state()
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not isinstance(h, RichHandler)]
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return startup_logger.setup_colored_logging("test_logger")


def test_setup_attaches_rich_handler(monkeypatch):
    log = _fresh_setup(monkeypatch, LOG_LEVEL="INFO", NO_COLOR="1")
    assert isinstance(log, logging.Logger)
    assert any(isinstance(h, RichHandler) for h in logging.getLogger().handlers)


def test_setup_respects_log_level(monkeypatch):
    _fresh_setup(monkeypatch, LOG_LEVEL="DEBUG", NO_COLOR="1")
    assert logging.getLogger().level == logging.DEBUG
    _fresh_setup(monkeypatch, LOG_LEVEL="WARNING", NO_COLOR="1")
    assert logging.getLogger().level == logging.WARNING


def test_setup_is_idempotent_no_duplicate_handlers(monkeypatch):
    _fresh_setup(monkeypatch, LOG_LEVEL="INFO", NO_COLOR="1")
    before = len([h for h in logging.getLogger().handlers if isinstance(h, RichHandler)])
    startup_logger.setup_colored_logging("test_logger")
    after = len([h for h in logging.getLogger().handlers if isinstance(h, RichHandler)])
    assert before == after == 1


def test_banner_and_checklist_do_not_crash(monkeypatch):
    _fresh_setup(monkeypatch, LOG_LEVEL="INFO", NO_COLOR="1")
    console = Console(record=True, no_color=True, width=100)
    startup_logger.print_startup_banner(console=console)
    statuses = startup_logger.log_startup_checklist(console=console)
    out = console.export_text()
    assert "DISCORD GPT" in out
    assert "Startup checks" in out
    assert "DISCORD_TOKEN" in statuses


def test_checklist_flags_missing_token(monkeypatch):
    _fresh_setup(monkeypatch, LOG_LEVEL="INFO", NO_COLOR="1")
    monkeypatch.setenv("DISCORD_TOKEN", "mock_discord_token")
    console = Console(record=True, no_color=True, width=100)
    statuses = startup_logger.log_startup_checklist(console=console)
    assert "API-ONLY" in statuses["DISCORD_TOKEN"]


def test_checklist_flags_valid_token(monkeypatch):
    _fresh_setup(monkeypatch, LOG_LEVEL="INFO", NO_COLOR="1")
    monkeypatch.setenv("DISCORD_TOKEN", "abcd1234567890xyz")
    console = Console(record=True, no_color=True, width=100)
    statuses = startup_logger.log_startup_checklist(console=console)
    assert "READY" in statuses["DISCORD_TOKEN"]


def test_helper_panels_do_not_crash():
    console = Console(record=True, no_color=True, width=100)
    startup_logger.log_api_only_mode(console=console)
    startup_logger.log_bot_ready("TestBot#1234", 3, console=console)
    startup_logger.log_sync_result(5, console=console)
    startup_logger.log_sync_failed(ValueError("boom"), console=console)
    out = console.export_text()
    assert "API-only" in out
    assert "TestBot#1234" in out
