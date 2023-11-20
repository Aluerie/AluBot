from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from utils import AluContext, const

if TYPE_CHECKING:
    from bot import AluBot

old_on_error = commands.Bot.on_error


async def on_error(self: AluBot, event: str, *args: Any, **kwargs: Any) -> None:
    """Called when an error is raised, and it's not from a command,
    but most likely from an event listener.

    Parameters
    ----------
    event: :class:`str`
        The name of the event that raised the exception.
    args: :class:`Any`
        The positional arguments for the event that raised the exception.
    kwargs: :class:`Any`
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

    # Event Arguments
    e = discord.Embed(title=f"`{event}`", colour=const.Colour.error_handler())
    e.set_author(name="Event Error")

    args_str = ["```py"]
    for index, arg in enumerate(args):
        args_str.append(f"[{index}]: {arg!r}")
    args_str.append("```")
    e.add_field(name="Args", value="\n".join(args_str), inline=False)
    e.set_footer(text="on_error (event error)")

    await self.exc_manager.register_error(exception, e, where=str(event))


async def setup(bot: AluBot):
    commands.Bot.on_error = on_error  # type: ignore # self is discord.Client while we want it AluBot.


async def teardown(bot: AluBot):
    commands.Bot.on_error = old_on_error
