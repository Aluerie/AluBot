from __future__ import annotations

import io
import json
import os
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

import discord
from discord.ext import commands

from cogs import get_extensions
from utils.checks import is_owner
from utils.context import Context
from utils.converters import Codeblock
from utils.var import MP, Cid, Clr, Ems, Sid

from ._twtvbot import TwitchBot

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context


class Integration(commands.Cog):

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        pass
        # await self.twitchbot.start()

    async def cog_unload(self) -> None:
        pass
    
    @commands.command()
    async def twitch_hi(self, ctx: Context):
        await self.bot.twitchbot.get_channel('Aluerie').send('yo')  # type: ignore
        await ctx.reply('done')