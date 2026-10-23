from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import const, mimics

from ._base import BaseDevCog

if TYPE_CHECKING:
    from core import AluInteraction, Bot


class Testing(BaseDevCog):



async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Testing(bot))
