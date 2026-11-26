# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Chatter."""

from __future__ import annotations

import contextlib
import datetime as dt
import random
from typing import TYPE_CHECKING, Any, ClassVar, Final, override

import discord
from discord.ext import commands

from core import Cog
from shared import clock, scheduler
from utils import const

if TYPE_CHECKING:
    from core import Bot

PERIODIC_MESSAGE_KEY: Final = "periodic-message"
"""Key of the one job that sends the periodic messages."""
CHAT_ACTIVE_WITHIN: Final = dt.timedelta(minutes=30)
"""A periodic message is only sent if somebody wrote in #general this recently: no talking to an empty room."""
CHAT_RECHECK_AFTER: Final = dt.timedelta(minutes=30)


def periodic_message_gap() -> dt.timedelta:
    """Pick the time until the next periodic message: a random one, a few weeks."""
    return dt.timedelta(
        weeks=random.randint(5, 10),
        days=random.randint(0, 7),
        hours=random.randint(0, 24),
        minutes=random.randint(0, 60),
    )


def next_periodic_message(_job: scheduler.Job[Any], now: dt.datetime) -> dt.datetime:
    """Repeat the periodic message job a random few weeks after it ran."""
    return now + periodic_message_gap()


# TODO: Write proper messages (embed fixer, birthday, colour roles)
PERIODIC_MESSAGES = [
    f"hey chat, {const.Emoji.peepoRoseDank}",
    "hey chat, be kind",
    "Hey chat, be nice.",
    f"Hey chat, fix your posture {const.Emoji.WeirdChamp}",
]


class Chatter(Cog):
    """Chatter."""

    MENTION_REACTIONS: ClassVar[tuple[str, ...]] = ("❔", "❕", "🤔")
    JOKE_CHANCE: ClassVar[float] = 1 / 400
    JOKE_MIN_WORDS: ClassVar[int] = 3
    JOKE_MAX_WORDS: ClassVar[int] = 12

    GENERAL_CHANNEL_ID: Final = const.ChannelId(702561315478044807)

    @discord.utils.cached_property
    def general_channel(self) -> discord.TextChannel:
        """General channel."""
        return self.bot.get_text_channel_or_test(self.GENERAL_CHANNEL_ID)

    @staticmethod
    def community_check(message: discord.Message) -> bool:
        """Community check."""
        if message.guild is None or message.guild.id != const.Guild.community:
            return False
        return not (message.author.bot or message.webhook_id)

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
        self.chat_active_at = message.created_at
        await self._react_to_mentions(message)
        await self._your_life_joke(message)

    # --- PERIODIC MESSAGES IN #GENERAL --------------------------------------------------------------------------------

    chat_active_at: dt.datetime | None = None
    """When a community member last wrote something (since the bot started)."""

    @override
    async def cog_load(self) -> None:
        # start the periodic messages if there's no job for them yet (a fresh database, or it was deleted)
        await self.bot.scheduler.schedule(
            "periodic_message",
            clock.utcnow() + periodic_message_gap(),
            key=PERIODIC_MESSAGE_KEY,
            guild_id=const.Guild.community,
            on_conflict="keep",
        )
        await super().cog_load()

    @scheduler.handler("periodic_message", recur=next_periodic_message)
    async def send_periodic_message(self, _job: scheduler.Job[Any]) -> scheduler.Reschedule | None:
        """Send an informational message in #general, once somebody is around to read it."""
        now = clock.utcnow()
        if self.chat_active_at is None or now - self.chat_active_at > CHAT_ACTIVE_WITHIN:
            return scheduler.Reschedule(now + CHAT_RECHECK_AFTER)

        embed = discord.Embed(
            title="Informational message",
            colour=0x122366,
            description=random.choice(PERIODIC_MESSAGES),
        )
        await self.general_channel.send(embed=embed)
        return None


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Chatter(bot))
