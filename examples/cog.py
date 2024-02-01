from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import const

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

from ._base import BaseCog


class MyCog(BaseCog):
    ...


async def setup(bot: AluBot) -> None:
    await bot.add_cog(MyCog(bot))
