from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, const
from utils.checks import is_owner

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class EmoteUtilitiesCog(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


async def setup(bot: AluBot):
    await bot.add_cog(EmoteUtilitiesCog(bot))
