from __future__ import annotations

try:
    # `?tag truststore` in discord.py server.
    # Why Windows is so bad with SSL?
    import truststore
except ImportError:
    pass
else:
    truststore.inject_into_ssl()

import asyncio
import logging
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

import aiohttp
import asyncpg
import click
import discord
import orjson

from bot import AluBot, setup_logging
from config import config
from utils import const

try:
    import uvloop  # type: ignore[reportMissingImports] # not available on Windows
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def create_pool() -> asyncpg.Pool[asyncpg.Record]:
    """Create a database connection pool."""

    def _encode_jsonb(value: Any) -> str:
        return orjson.dumps(value).decode("utf-8")

    def _decode_jsonb(value: str) -> Any:
        return orjson.loads(value)

    async def init(con: asyncpg.Connection[asyncpg.Record]) -> None:
        await con.set_type_codec(
            "jsonb",
            schema="pg_catalog",
            encoder=_encode_jsonb,
            decoder=_decode_jsonb,
            format="text",
        )

    postgres_url = config["POSTGRES"]["VPS"] if platform.system() == "Linux" else config["POSTGRES"]["HOME"]
    return await asyncpg.create_pool(
        postgres_url,
        init=init,
        command_timeout=60,
        min_size=20,
        max_size=20,
        statement_cache_size=0,
    )  # type: ignore[reportReturnType]


async def start_the_bot(*, test: bool) -> None:
    """Helper function to start the bot."""
    log = logging.getLogger()
    try:
        pool = await create_pool()
    except Exception:
        msg = "Could not set up PostgreSQL. Exiting."
        click.echo(msg, file=sys.stderr)
        log.exception(msg)
        if platform.system() != "Windows":
            session = aiohttp.ClientSession()
            webhook = discord.Webhook.from_url(
                url=config["WEBHOOKS"]["SPAM"],
                session=session,
            )
            embed = discord.Embed(color=const.Color.error, description=msg)
            await webhook.send(content=const.Role.error.mention, embed=embed)
            await session.close()
        return
    else:
        async with (
            aiohttp.ClientSession() as session,
            pool as pool,
            AluBot(test=test, session=session, pool=pool) as alubot,
        ):
            await alubot.start()


@click.group(invoke_without_command=True, options_metavar="[options]")
@click.pass_context
@click.option("--test", "-t", is_flag=True)
def main(click_ctx: click.Context, *, test: bool) -> None:
    """Launches the bot."""
    if click_ctx.invoked_subcommand is None:
        with setup_logging(test=test):
            try:
                asyncio.run(start_the_bot(test=test))
            except KeyboardInterrupt:
                print("Aborted! The bot was interrupted with `KeyboardInterrupt`!")  # noqa: T201


@main.group(short_help="database stuff", options_metavar="[options]")
def db() -> None:
    """Group for cli database related commands."""


@db.command()
def create() -> None:
    """Creates the database tables."""
    try:

        async def run_create() -> None:
            connection = await asyncpg.connect(config["POSTGRES"]["HOME"])
            async with connection.transaction():
                for f in Path("sql").iterdir():
                    if f.is_file() and f.suffix == ".sql" and not f.name.startswith("_"):
                        sql = f.read_text("utf-8")
                        await connection.execute(sql)

        asyncio.run(run_create())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        click.secho("failed to apply SQL due to error", fg="red")
    else:
        click.secho("Applied SQL tables", fg="green")


if __name__ == "__main__":
    main()
