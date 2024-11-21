from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import const

from ._base import BaseCog

if TYPE_CHECKING:
    from bot import AluBot, AluContext


class MyCog(BaseCog): ...


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(MyCog(bot))
