from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
import logging
import sys
import traceback
from pathlib import Path

import asyncpg
import click

from cogs.utils.database import create_pool
from cogs.utils.bot import AluBot, setup_logging

if TYPE_CHECKING:
    pass


async def bot_run(test: bool):
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
            asyncio.run(bot_run(test))


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
