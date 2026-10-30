"""Chatter.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
import random
from typing import TYPE_CHECKING, ClassVar, Final, TypedDict

import discord
from discord.ext import commands

from core import Cog, Timer
from shared import clock
from utils import const

if TYPE_CHECKING:
    from core import Bot

    class PeriodicMessageTimerData(TypedDict):
        """PeriodicMessageTimerData."""

        index: int


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# TODO: Write proper messages (embed fixer, birthday, colour roles)
PERIODIC_MESSAGES = [
    f"hey chat, {const.Emoji.peepoRoseDank}",
    "hey chat, be kind",
    "Hey chat, be nice.",
    "Hey chat, fix your posture {const.Emoji.peepoRoseDank}"
]


class Chatter(Cog):
    """Chatter."""

    MENTION_REACTIONS: ClassVar[tuple[str, ...]] = ("❔", "❕", "🤔")
    JOKE_CHANCE: ClassVar[float] = 1 / 400
    JOKE_MIN_WORDS: ClassVar[int] = 3
    JOKE_MAX_WORDS: ClassVar[int] = 12

    GENERAL_CHANNEL_ID: Final = const.ChannelId(702561315478044807)

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

    @discord.utils.cached_property
    def general_channel(self) -> discord.TextChannel:
        """General channel."""
        return self.bot.get_text_channel_or_test(self.GENERAL_CHANNEL_ID)

    @staticmethod
    def community_check(message: discord.Message) -> bool:
        """Community check."""
        if message.guild is None or message.guild.id != const.Guild.community:
            return False
        if message.author.bot or message.webhook_id:  # ruff: ignore[needless-bool]
            return False
        return True

    # --- FLAVOUR ------------------------------------------------------------------------------------------------------

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

    # --- LISTENER DISPATCH --------------------------------------------------------------------------------------------

    @commands.Cog.listener("on_message")
    async def chatter(self, message: discord.Message) -> None:
        """React and respond to community member's messages."""
        if not self.community_check(message):
            return
        await self._react_to_mentions(message)
        await self._your_life_joke(message)

    # --- PERIODIC MESSAGES IN #GENERAL --------------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_periodic_message_timer_complete(self, timer: Timer[PeriodicMessageTimerData]) -> None:
        """On periodic message timer complete.

        Periodically send informational messages in general.
        """
        index = timer.data["index"]
        await self.bot.wait_for("message", check=self.community_check)
        await asyncio.sleep(random.randrange(5, 10))
        embed = discord.Embed(
            title="Informational message",
            colour=0x122366,
            description=PERIODIC_MESSAGES[index % len(PERIODIC_MESSAGES)],
        )
        await self.general_channel.send(embed=embed)
        await self.bot.timers.cleanup(timer.id)
        data: PeriodicMessageTimerData = {"index": index}
        await self.bot.timers.create(
            event="periodic_message",
            expires_at=(
                clock.utcnow()
                + dt.timedelta(
                    weeks=random.randint(5, 10),
                    days=random.randint(0, 7),
                    hours=random.randint(0, 24),
                    minutes=random.randint(0, 60),
                )
            ),
            data=data,
        )


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Chatter(bot))
