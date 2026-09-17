"""Global color-coded console logging for the Discord bot.

Uses ``rich`` for level colors, pretty tracebacks, a startup banner,
and a config checklist so ``python -m src.main`` looks cool and
misconfiguration is obvious at a glance.
"""

from __future__ import annotations

import logging
import os
import platform
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.traceback import install as install_rich_traceback

APP_NAME = "DISCORD GPT"
APP_VERSION = "1.0.0"

_CONSOLE: Console | None = None
_CONFIGURED = False

# Noisy third-party loggers that drown out our own output unless debugging.
_QUIET_LOGGERS = (
    "discord",
    "discord.http",
    "discord.gateway",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "sqlalchemy.engine",
    "apscheduler",
)


def get_console() -> Console:
    """Return a shared Rich console (respects NO_COLOR / piped output)."""
    global _CONSOLE
    if _CONSOLE is None:
        no_color = os.getenv("NO_COLOR") is not None or not sys.stdout.isatty()
        # When piped, Rich strips ANSI automatically; no_color covers CI/NO_COLOR.
        _CONSOLE = Console(no_color=no_color)
    return _CONSOLE


def reset_logging_state() -> None:
    """Reset module state (used by tests to re-configure logging)."""
    global _CONSOLE, _CONFIGURED
    _CONSOLE = None
    _CONFIGURED = False


def setup_colored_logging(logger_name: str | None = None) -> logging.Logger:
    """Configure root logging with a Rich handler (idempotent).

    Colors: DEBUG=cyan, INFO=green, WARNING=yellow,
    ERROR=bold red, CRITICAL=white-on-red (via Rich defaults +
    explicit level width). Returns the requested logger.
    """
    global _CONFIGURED

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    console = get_console()

    if not _CONFIGURED:
        # Pretty tracebacks for uncaught errors during startup.
        try:
            install_rich_traceback(show_locals=False, console=console)
        except Exception:
            pass

        root = logging.getLogger()
        root.setLevel(level)
        has_rich = any(isinstance(h, RichHandler) for h in root.handlers)
        if not has_rich:
            handler = RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
                markup=True,
                log_time_format="[%X]",
            )
            handler.setLevel(level)
            root.addHandler(handler)

        # Keep discord.py / uvicorn / sqlalchemy readable by default.
        if level > logging.DEBUG:
            for name in _QUIET_LOGGERS:
                logging.getLogger(name).setLevel(logging.WARNING)

        _CONFIGURED = True
    else:
        logging.getLogger().setLevel(level)

    return logging.getLogger(logger_name or "discord_agent")


def _mask_token(token: str) -> str:
    token = token.strip()
    if not token or token == "mock_discord_token":
        return "missing"
    if len(token) <= 10:
        return "***"
    return f"{token[:4]}...{token[-3:]} ({len(token)} chars)"


def print_startup_banner(console: Console | None = None) -> None:
    """Print the cool startup banner panel."""
    console = console or get_console()
    try:
        import discord

        discord_version = getattr(discord, "__version__", "?")
    except Exception:
        discord_version = "?"

    env = os.getenv("ENV", "development")
    port = os.getenv("PORT", "8000")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    banner_text = (
        f"[bold magenta]{APP_NAME}[/] [dim]v{APP_VERSION}[/]\n"
        f"[cyan]env:[/] {env}   [cyan]python:[/] {platform.python_version()}   "
        f"[cyan]discord.py:[/] {discord_version}\n"
        f"[cyan]port:[/] {port}   [cyan]log:[/] {log_level}"
    )
    console.print(Panel(banner_text, title="bot starting", border_style="magenta", expand=False))


def log_startup_checklist(
    console: Console | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, str]:
    """Print a color-coded config checklist table. Returns {check: status}."""
    console = console or get_console()
    log = logger or logging.getLogger("discord_agent_main")

    token = os.getenv("DISCORD_TOKEN", "mock_discord_token")
    db_url = os.getenv("DATABASE_URL", "")
    redis_url = os.getenv("REDIS_URL", "")
    threshold = os.getenv("NEEDLE_CONFIDENCE_THRESHOLD", "0.5")

    try:
        from src.actions.registry import ActionRegistry

        tool_count = str(len(ActionRegistry.get_all()))
    except Exception:
        tool_count = "?"

    token_ok = token.strip() not in ("", "mock_discord_token")

    rows: list[tuple[str, str, str]] = [
        (
            "DISCORD_TOKEN",
            _mask_token(token),
            "[green]READY[/]" if token_ok else "[yellow]API-ONLY[/]",
        ),
        (
            "DATABASE_URL",
            "set" if db_url else "missing",
            "[green]OK[/]" if db_url else "[red]MISSING[/]",
        ),
        (
            "REDIS_URL",
            "set" if redis_url else "missing",
            "[green]OK[/]" if redis_url else "[yellow]NOT SET[/]",
        ),
        ("NEEDLE_THRESHOLD", threshold, "[green]OK[/]"),
        ("REGISTERED_TOOLS", tool_count, "[green]OK[/]" if tool_count != "?" else "[dim]?[/]"),
    ]

    table = Table(title="Startup checks", header_style="bold cyan", border_style="dim")
    table.add_column("Check", style="bold")
    table.add_column("Value")
    table.add_column("Status", justify="right")
    statuses: dict[str, str] = {}
    for check, value, status in rows:
        table.add_row(check, value, status)
        statuses[check] = status

    console.print(table)

    if not token_ok:
        log.warning("No valid DISCORD_TOKEN provided. Running in API-only / test mode.")
    if not db_url:
        log.error("DATABASE_URL is missing - /ready checks and DB features will fail.")
    return statuses


def log_api_only_mode(console: Console | None = None) -> None:
    """Highlight API-only mode with a yellow panel."""
    (console or get_console()).print(
        Panel(
            "No valid DISCORD_TOKEN - serving FastAPI only.\n"
            "Set DISCORD_TOKEN in .env to connect the Discord gateway.",
            title="API-only mode",
            border_style="yellow",
            expand=False,
        )
    )


def log_bot_ready(
    bot_user: object,
    guild_count: int | None = None,
    console: Console | None = None,
) -> None:
    """Highlight successful gateway connect with a green panel."""
    (console or get_console()).print(
        Panel(
            f"Connected as [bold green]{bot_user}[/]"
            + (f"  |  [cyan]{guild_count} guild(s)[/]" if guild_count is not None else ""),
            title="bot online",
            border_style="green",
            expand=False,
        )
    )


def log_sync_result(count: int, console: Console | None = None) -> None:
    (console or get_console()).print(f"[green]Synced {count} slash command(s).[/green]")


def log_sync_failed(exc: BaseException, console: Console | None = None) -> None:
    (console or get_console()).print(
        Panel(
            f"[bold red]Failed to sync commands:[/] {exc}",
            title="sync error",
            border_style="red",
            expand=False,
        )
    )
