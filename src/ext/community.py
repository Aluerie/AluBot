"""Community Features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import contextlib
import logging
import random
from typing import TYPE_CHECKING, ClassVar, Final, override

import discord
from discord.ext import commands

from config import env
from core import Cog
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from core import Bot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Community(Cog):
    """Community Features."""

    DOTA_STEAM_DB_UPDATES_CHANNEL_ID: Final = 873430376033452053

    MENTION_REACTIONS: ClassVar[tuple[str, ...]] = ("❔", "❕", "🤔")
    JOKE_CHANCE: ClassVar[float] = 1 / 300
    JOKE_MIN_WORDS: ClassVar[int] = 3
    JOKE_MAX_WORDS: ClassVar[int] = 12

    LIVE_STREAMER_ROLE_ID: Final = 760082390059581471

    @override
    async def cog_load(self) -> None:
        self.restart_clean_up.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.restart_clean_up.cancel()
        await super().cog_unload()

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
        words = message.content.split()
        if not (self.JOKE_MIN_WORDS <= len(words) <= self.JOKE_MAX_WORDS):
            return
        if random.random() >= self.JOKE_CHANCE:
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

    ####################################################################################################################
    # STEAM DB REPOSTING
    ####################################################################################################################

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        """Webhook to send Dota 2 News to."""
        webhook_url = env.WEBHOOK_DOTANEWS if not self.bot.test else env.WEBHOOK_SPAM
        return self.bot.webhook_from_url(webhook_url)

    @commands.Cog.listener("on_message")
    async def filter_steam_db_messages(self, message: discord.Message) -> None:
        """Filter SteamDB messages from uninteresting ones.

        That channel contains all kind of updates, but we are only interested in blogpost ones.

        Warning
        -------
        Reposting from steamDB resources is rude and copyright-tier bad.
        Please, think of other ways to implement this (e.g. ISteamNews/GetNewsForApp or RSS feed)
        """
        if message.channel.id != self.DOTA_STEAM_DB_UPDATES_CHANNEL_ID:
            return
        if "https://steamcommunity.com" not in message.content:
            return

        msg = await self.news_webhook.send(content=f"# {message.content}", wait=True)
        await msg.publish()

    ####################################################################################################################
    # LIVE STREAMER
    ####################################################################################################################

    @staticmethod
    def _is_streaming(member: discord.Member) -> bool:
        """Return whether the member has a streaming activity on any platform."""
        return any(isinstance(a, discord.Streaming) for a in member.activities)

    async def _sync_streamer_role(self, member: discord.Member, role: discord.Role) -> None:
        """Add or remove the streamer role so it matches the member's streaming activity.

        Parameters
        ----------
        member
            The member to update.
        role
            The @LiveStreamer role.
        """
        is_streaming = self._is_streaming(member)
        has_role = role in member.roles

        if is_streaming and not has_role:
            await member.add_roles(role, reason="Started streaming")
        elif not is_streaming and has_role:
            await member.remove_roles(role, reason="Stopped streaming")

    @commands.Cog.listener(name="on_presence_update")
    async def community_streamer_role_management(self, before: discord.Member, after: discord.Member) -> None:
        """Detect community members who are currently streaming and grant them @LiveStreamer role."""
        if after.guild.id != const.Guild.community or after.bot:
            return
        if self._is_streaming(before) == self._is_streaming(after):
            return
        await self._sync_streamer_role(after, self.bot.get_role(after.guild.id, self.LIVE_STREAMER_ROLE_ID))

    @loop(count=1, wait_for_ready=True)
    async def restart_clean_up(self) -> None:
        """Resync @LiveStreamer role after a restart.

        The bot can be offline for a long time, so presence events are missed.
        """
        role = self.bot.get_role(const.Guild.community, self.LIVE_STREAMER_ROLE_ID)
        for member in role.guild.members:
            if not member.bot:
                await self._sync_streamer_role(member, role)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Community(bot))
