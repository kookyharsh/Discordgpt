import logging
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.models import Base

load_dotenv()

logger = logging.getLogger("discord_agent.db")


def _normalize_url(raw: str) -> str:
    """Make a Prisma-style Postgres URL work with SQLAlchemy+asyncpg.

    - postgresql:// -> postgresql+asyncpg://
    - drops ?pgbouncer=true (Prisma-ism, invalid for asyncpg)
    """
    scheme, netloc, path, query, frag = urlsplit(raw)
    if scheme == "postgresql":
        scheme = "postgresql+asyncpg"
    params = [(k, v) for k, v in parse_qsl(query) if k.lower() != "pgbouncer"]
    return urlunsplit((scheme, netloc, path, urlencode(params), frag))


def _resolve_url() -> tuple[str, dict]:
    # Prefer DIRECT_URL (session/direct connection): the 6543 transaction
    # pooler breaks asyncpg prepared statements, so only use DATABASE_URL
    # when it isn't the transaction pooler.
    direct = os.getenv("DIRECT_URL")
    url = os.getenv("DATABASE_URL") or ""
    if ":6543/" in url and direct:
        logger.info("DATABASE_URL is a transaction pooler; using DIRECT_URL instead")
        url = direct
    if not url:
        url = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/discord_agent"
    url = _normalize_url(url)
    connect_args: dict = {}
    if "supabase" in (urlsplit(url).hostname or ""):
        connect_args["ssl"] = "require"
    return url, connect_args


DATABASE_URL, _CONNECT_ARGS = _resolve_url()

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_CONNECT_ARGS)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
