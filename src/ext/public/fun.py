"""Fun.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from core import Cog

if TYPE_CHECKING:
    from core import AluBot, Interaction


class FunCog(Cog):
    """Fun Cog."""

    @app_commands.command(name="coin-flip")
    async def coin_flip(self, interaction: Interaction) -> None:
        """🪙 Flip a coin: Heads or Tails?"""  # ruff: ignore[missing-trailing-period]
        word = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(content=word, file=discord.File(f"assets/images/coinflip/{word}.png"))


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FunCog(bot))
