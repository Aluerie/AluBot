from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from pathlib import Path

import aiohttp
import asyncpg
import click

from bot import AluBot, setup_logging
from config import POSTGRES_URL
from utils.database import create_pool

try:
    import uvloop  # type: ignore # not available on Windows
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def start_the_bot(test: bool) -> None:
    """Helper function to start the bot."""
    log = logging.getLogger()
    try:
        pool = await create_pool()
    except Exception:
        click.echo("Could not set up PostgreSQL. Exiting.", file=sys.stderr)
        log.exception("Could not set up PostgreSQL. Exiting.")
        # todo: maybe webhook notif that it went wrong
        return

    async with aiohttp.ClientSession() as session, pool as pool, AluBot(test, session=session, pool=pool) as alubot:
        await alubot.start()


@click.group(invoke_without_command=True, options_metavar="[options]")
@click.pass_context
@click.option("--test", "-t", is_flag=True)
def main(click_ctx: click.Context, test: bool) -> None:
    """Launches the bot."""
    if click_ctx.invoked_subcommand is None:
        with setup_logging(test):
            asyncio.run(start_the_bot(test))


@main.group(short_help="database stuff", options_metavar="[options]")
def db() -> None:
    """Group for cli database related commands."""
    pass


@db.command()
def create() -> None:
    """Creates the database tables."""
    try:

        async def run_create() -> None:
            connection = await asyncpg.connect(POSTGRES_URL)
            async with connection.transaction():
                for f in Path("sql").iterdir():
                    if f.is_file() and f.suffix == ".sql" and not f.name.startswith("_"):
                        sql = f.read_text("utf-8")
                        await connection.execute(sql)

        asyncio.run(run_create())
    except Exception:
        traceback.print_exc()
        click.secho("failed to apply SQL due to error", fg="red")
    else:
        click.secho("Applied SQL tables", fg="green")


if __name__ == "__main__":
    main()
