"""Python file to launch the bot with, so called "main".

Generally, it's preferred to use `make run` to run this bot, however you can use
`uv run src/main.py`, `python src/main.py`, etc. if you like.
CLI supported flags can be viewed with `--help` flag.

License
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio

try:
    # `?tag truststore` in discord.py server. Unfortunately, on average, Windows is very bad with SSL.
    import truststore  # ty: ignore[unresolved-import] "if it doesn't work" measure, we don't need to install this.
except ImportError:
    pass
else:
    truststore.inject_into_ssl()


import aiohttp
import click

from config import env
from core import Bot
from shared import ut
from shared.concepts import db, logs

# generated at https://patorjk.com/software/taag/ using "Standard" font
ASCII_STARTING_UP_ART = r"""
     _    _       ____        _     ____  _             _   _
    / \  | |_   _| __ )  ___ | |_  / ___|| |_ __ _ _ __| |_(_)_ __   __ _
   / _ \ | | | | |  _ \ / _ \| __| \___ \| __/ _` | '__| __| | '_ \ / _` |
  / ___ \| | |_| | |_) | (_) | |_   ___) | || (_| | |  | |_| | | | | (_| |
 /_/   \_\_|\__,_|____/ \___/ \__| |____/ \__\__,_|_|   \__|_|_| |_|\__, |
                                                                    |___/
            [ ALUBOT IS STARTING NOW ]
"""


async def start_the_bot(
    *,
    is_subset_mode: bool,
    is_test_account: bool,
) -> None:
    """Start the bot."""
    async with (
        aiohttp.ClientSession() as session,
        await db.try_create_pool(
            env.POSTGRES_PROD,
            env.POSTGRES_TEST,
            is_test=is_test_account,
        ) as pool,
        Bot(
            session=session,
            pool=pool,
            is_subset_mode=is_subset_mode,
            is_test_account=is_test_account,
        ) as alubot,
    ):
        await alubot.start()


@click.group(invoke_without_command=True, options_metavar="[options]")
@click.pass_context
@click.option(
    "--subset-mode",
    "-u",
    is_flag=True,
    default=False,  # usual default: False ✅
    help=(
        "Whether to launch the bot in subset-mode. "
        "In this mode the bot only loads extensions that are listed in `ext_subset.py` file."
        "Useful for debugging as it makes launch times much faster."
    ),
)
@click.option(
    "--test-account",
    "-t",
    is_flag=True,
    default=False,  # usual default: False ✅
    help=(
        "Whether to launch the bot using test dummy account (@YenBot) or real account (@AluBot). "
        "It's useful when we want to test some features without interrupting the main account."
    ),
)
def launch(
    click_ctx: click.Context,
    *,
    subset_mode: bool,
    test_account: bool,
) -> None:
    """Launch the bot."""
    if click_ctx.invoked_subcommand is None:
        with logs.setup_logging(
            starting_up_art=ASCII_STARTING_UP_ART,
            filename="alubot.log",
        ):
            try:
                ut.run(
                    start_the_bot(
                        is_subset_mode=subset_mode,
                        is_test_account=test_account,
                    )
                )
            except KeyboardInterrupt:
                print("Aborted! The bot was interrupted with `KeyboardInterrupt`!")  # ruff: ignore[print]
            except asyncio.CancelledError:
                print("Aborted! The bot was interrupted with `asyncio.CancelledError`!")  # ruff: ignore[print]


if __name__ == "__main__":
    launch()
