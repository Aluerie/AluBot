from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from bot import AluContext
from utils import const

if TYPE_CHECKING:
    from bot import AluBot

old_on_error = commands.Bot.on_error


async def on_error(self: AluBot, event: str, *args: Any, **kwargs: Any) -> None:
    """Called when an error is raised in an event listener.

    Parameters
    ----------
    event: str
        The name of the event that raised the exception.
    args: Any
        The positional arguments for the event that raised the exception.
    kwargs: Any
        The keyword arguments for the event that raised the exception.

    """
    # Exception Traceback
    (_exception_type, exception, _traceback) = sys.exc_info()
    if exception is None:
        exception = TypeError("Somehow `on_error` fired with exception being `None`.")

    # Silence command errors that somehow get bubbled up far enough here
    # if isinstance(exception, commands.CommandInvokeError):
    #     return

    # ridiculous attempt to eliminate 404 that appear for Hybrid commands for my own usage.
    # that I can't really remove via on_command_error since they appear before we can do something about it.
    # maybe we need some rewrite about it tho; like ignore all discord.HTTPException
    if (
        isinstance(args[0], AluContext)
        and args[0].author.id == const.User.aluerie
        and isinstance(exception, discord.NotFound)
    ):
        return

    embed = (
        discord.Embed(
            colour=0xA32952,
            title=f"`{event}`",
        )
        .set_author(name="Event Error")
        .add_field(
            name="Args",
            value=(
                "```py\n" + "\n".join(f"[{index}]: {arg!r}" for index, arg in enumerate(args)) + "```"
                if args
                else "No Args"
            ),
            inline=False,
        )
        .set_footer(text=f"AluBot.on_error: {event}")
    )
    await self.exc_manager.register_error(exception, embed)


async def setup(_: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    commands.Bot.on_error = on_error  # type: ignore # self is discord.Client while we want it AluBot.


async def teardown(_: AluBot) -> None:
    """Unload AluBot extension. Framework of discord.py."""
    commands.Bot.on_error = old_on_error
