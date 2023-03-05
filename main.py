from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import coroutine
from typing import TYPE_CHECKING

import asyncpg
import click
from cogs import get_extensions

from utils.bot import AluBot, get_log_fmt
from utils.database import create_pool

if TYPE_CHECKING:
    pass

try:
    import uvloop  # type: ignore
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@contextmanager
def setup_logging(test: bool):
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    try:
        # Stream Handler
        handler = logging.StreamHandler()
        handler.setFormatter(get_log_fmt(handler))
        log.addHandler(handler)

        # ensure logs folder
        Path(".logs/").mkdir(parents=True, exist_ok=True)
        # File Handler
        file_handler = RotatingFileHandler(
            filename=f'.logs/alubot{"" if not test else "_test"}.log',
            encoding='utf-8',
            mode='w',
            maxBytes=16 * 1024 * 1024,  # 16 MiB
            backupCount=5,  # Rotate through 5 files
        )
        file_handler.setFormatter(get_log_fmt(file_handler))
        log.addHandler(file_handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)


async def bot_start(test: bool):
    log = logging.getLogger()
    try:
        pool = await create_pool()
    except Exception:
        click.echo('Could not set up PostgreSQL. Exiting.', file=sys.stderr)
        log.exception('Could not set up PostgreSQL. Exiting.')
        return

    async with AluBot(test) as bot:
        bot.pool = pool
        await bot.my_start()


@click.group(invoke_without_command=True, options_metavar='[options]')
@click.pass_context
@click.option('--test', '-t', is_flag=True)
def main(click_ctx: click.Context, test: bool):
    """Launches the bot."""

    if click_ctx.invoked_subcommand is None:
        with setup_logging(test):
            asyncio.run(bot_start(test))


@main.group(short_help='database stuff', options_metavar='[options]')
def db():
    pass


@db.command()
def create():
    """Creates the database tables."""
    try:

        async def run_create():
            connection: asyncpg.Connection = await asyncpg.connect(POSTGRES_URL)  # type: ignore
            async with connection.transaction():
                sql = Path('sql/tables.sql').read_text('utf-8')
                await connection.execute(sql)

        asyncio.run(run_create())
    except Exception:
        traceback.print_exc()
        click.secho('failed to apply SQL due to error', fg='red')
    else:
        click.secho(f'Applied SQL tables', fg='green')


if __name__ == '__main__':
    main()
