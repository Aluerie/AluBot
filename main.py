import asyncio
import sys
import logging
from pathlib import Path
import traceback

import asyncpg
import click

from config import POSTGRES_URL
from cogs.utils.bot import AluBot, setup_logging


class DRecord(asyncpg.Record):  # Dot Record - allows dot-notations
    def __getattr__(self, name):
        return self[name]


async def bot_run(test: bool):
    log = logging.getLogger()
    try:
        pool = await asyncpg.create_pool(
            POSTGRES_URL,
            min_size=10,
            max_size=10,
            record_class=DRecord,
            statement_cache_size=0
        )
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
def main(click_ctx, test):
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
                sql = Path('SQL/tables.sql').read_text('utf-8')
                await connection.execute(sql)

        asyncio.run(run_create())
    except Exception:
        traceback.print_exc()
        click.secho('failed to apply SQL due to error', fg='red')
    else:
        click.secho(f'Applied SQL tables', fg='green')


if __name__ == '__main__':
    main()
