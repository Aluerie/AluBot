"""Chatter.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import contextlib
import logging
import random
from typing import TYPE_CHECKING, ClassVar

import discord
from discord.ext import commands

from core import Cog
from utils import const

if TYPE_CHECKING:
    from core import Bot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Chatter(Cog):
    """Chatter."""

    MENTION_REACTIONS: ClassVar[tuple[str, ...]] = ("❔", "❕", "🤔")
    JOKE_CHANCE: ClassVar[float] = 1 / 400
    JOKE_MIN_WORDS: ClassVar[int] = 3
    JOKE_MAX_WORDS: ClassVar[int] = 12

    ####################################################################################################################
    # CHATTER
    ####################################################################################################################

    async def _react_to_mentions(self, message: discord.Message) -> None:
        """React with confused emojis if the bot is mentioned."""
        if self.bot.user not in message.mentions:
            return
        with contextlib.suppress(discord.HTTPException):
            for r in self.MENTION_REACTIONS:
                await message.add_reaction(r)

    async def _your_life_joke(self, message: discord.Message) -> None:
        """Occasionally reply with "Your life ..." replacing the first two words."""
        if random.random() >= self.JOKE_CHANCE:
            return
        words = message.content.split()
        if not (self.JOKE_MIN_WORDS <= len(words) <= self.JOKE_MAX_WORDS):
            return
        await message.channel.send("Your life " + " ".join(words[2:]), allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener("on_message")
    async def chatter(self, message: discord.Message) -> None:
        """React and respond to community member's messages."""
        if message.guild is None or message.guild.id != const.Guild.community:
            return
        if message.author.bot or message.webhook_id:
            return
        await self._react_to_mentions(message)
        await self._your_life_joke(message)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Chatter(bot))
