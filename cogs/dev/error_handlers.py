from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sys

import traceback

import discord
from discord.ext import commands

from ._base import DevBaseCog

from utils import const

if TYPE_CHECKING:
    from utils import AluBot, AluContext


# class ErrorHandlersCog(DevBaseCog):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     @commands.Cog.listener()
#     async def on_command_error(self, ctx: AluContext, error: Exception) -> None:
#         if ctx.is_error_handled is True:
#             # TODO: it's is `error_handled` everywhere tho
#             return

#         error = getattr(error, 'original', error)

#         match error:
#             case _:
#                 return

old_on_error = commands.Bot.on_error  # future #TODO: replace with AutoShardedBot

async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
    """Replace"""

    # Exception Traceback
    (_exc_type, exc, _tb) = sys.exc_info()

    # Event Arguments
    e = discord.Embed(title=f'`{event}`', colour=const.Colour.error_handler())
    e.set_author(name='Event Error')

    args_str = ['```py']
    for index, arg in enumerate(args):
        args_str.append(f'[{index}]: {arg!r}')
    args_str.append('```')
    e.add_field(name='Args', value='\n'.join(args_str), inline=False)

    await self.send_exception(exc, e)


async def setup(bot: AluBot):
    commands.Bot.on_error = on_error

async def teardown(bot: AluBot):
    commands.Bot.on_error = old_on_error