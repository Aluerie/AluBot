from __future__ import annotations

import contextlib
import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core import AluCog
from utils import const

if TYPE_CHECKING:
    from core import AluBot, AluInteraction


class FunOther(AluCog):
    @app_commands.command()
    async def coinflip(self, interaction: AluInteraction) -> None:
        """Flip a coin: Heads or Tails?."""
        word = "Heads" if random.randint(0, 1) == 0 else "Tails"
        await interaction.response.send_message(content=word, file=discord.File(f"assets/images/coinflip/{word}.png"))

    # TODO: this should be somewhere else
    @commands.Cog.listener("on_message")
    async def reply_non_command_mentions(self, message: discord.Message) -> None:
        """For now there is only blush and question marks."""
        if message.guild and message.guild.me in message.mentions:
            if any(item in message.content.lower() for item in ["😊", "blush"]):
                await message.channel.send(f"{message.author.mention} {const.Emote.peepoBlushDank}")
            else:
                ctx = await self.bot.get_context(message)
                if ctx.command:
                    return
                for r in ["❔", "❕", "🤔"]:
                    with contextlib.suppress(discord.HTTPException):
                        await message.add_reaction(r)

    @app_commands.command()
    async def roll(self, interaction: AluInteraction, max_roll_number: app_commands.Range[int, 1]) -> None:
        """Roll an integer from 1 to `max_roll_number`.

        Parameters
        ----------
        max_roll_number: app_commands.Range[int, 1]
            Max limit to roll.

        """
        await interaction.response.send_message(content=str(random.randint(1, max_roll_number + 1)))


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FunOther(bot))
