"""Community Features.

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
from typing import TYPE_CHECKING, ClassVar, Final, override

import discord
from discord.ext import commands

from config import env
from core import Cog
from shared import clock, globs
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core import Bot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Community(Cog):
    """Community Features."""

    HIDEOUT_STEAM_DB_CHANNEL_ID: Final = 873430376033452053
    BOT_SPAM_CHANNEL_ID: Final = 724986090632642653
    HIDEOUT_SPAM_CHANNEL_ID: Final = 970823670702411810

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
        if message.channel.id != self.HIDEOUT_STEAM_DB_CHANNEL_ID:
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

    ####################################################################################################################
    # LOGGER
    ####################################################################################################################

    @discord.utils.cached_property
    def bot_spam_channel(self) -> discord.TextChannel:
        """Webhook to send Dota 2 News to."""
        channel_id = self.BOT_SPAM_CHANNEL_ID if not self.bot.test else self.HIDEOUT_SPAM_CHANNEL_ID
        return self.bot.get_text_channel(channel_id)

    @staticmethod
    def _emoji_embed(
        title: str,
        color: int,
        emoji: discord.Emoji,
        description: str,
        actor: discord.Member | discord.User | None,
    ) -> discord.Embed:
        embed = discord.Embed(color=color, title=title, description=description).set_thumbnail(url=emoji.url)
        if actor is not None:
            embed.set_author(name=actor.display_name, icon_url=actor.display_avatar.url)
        elif emoji.managed:
            embed.set_author(name="Managed by an integration", icon_url=globs.Logo.Twitch)
        return embed

    async def _find_emoji_actor(
        self, guild: discord.Guild, action: discord.AuditLogAction, emoji: discord.Emoji
    ) -> discord.Member | discord.User | None:
        if emoji.managed:
            return None  # synced by an integration, so there's no audit log entry

        cutoff = clock.utcnow() - dt.timedelta(seconds=15)
        for _ in range(3):
            try:
                async for entry in guild.audit_logs(limit=10, action=action):
                    if entry.created_at < cutoff:
                        break
                    if entry.target is not None and entry.target.id == emoji.id:
                        return entry.user
            except discord.Forbidden:
                log.warning("Missing View Audit Log permission in %s", guild)
                return None
            await asyncio.sleep(1)
        return None

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: Sequence[discord.Emoji],
        after: Sequence[discord.Emoji],
    ) -> None:
        """Log emoji additions, removals, and edits to the bot spam channel."""
        expected_guild = const.Guild.hideout if self.bot.test else const.Guild.community
        if guild.id != expected_guild:
            return

        old = {e.id: e for e in before}
        new = {e.id: e for e in after}

        for emoji_id in new.keys() - old.keys():
            emoji = new[emoji_id]
            actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_create, emoji)
            embed = self._emoji_embed("Emote added", 0x00FF7F, emoji, f"`:{emoji.name}:`", actor)
            await self.bot_spam_channel.send(embed=embed)

        for emoji_id in old.keys() - new.keys():
            emoji = old[emoji_id]
            actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_delete, emoji)
            embed = self._emoji_embed("Emote removed", 0xFF4500, emoji, f"`:{emoji.name}:`", actor)
            await self.bot_spam_channel.send(embed=embed)

        for emoji_id in old.keys() & new.keys():
            b, a = old[emoji_id], new[emoji_id]
            changes = []
            if b.name != a.name:
                changes.append(f"**Name:** `{b.name}` -> `{a.name}`")
            if {r.id for r in b.roles} != {r.id for r in a.roles}:
                before_roles = ", ".join(r.mention for r in b.roles) or "everyone"
                after_roles = ", ".join(r.mention for r in a.roles) or "everyone"
                changes.append(f"**Roles:** {before_roles} -> {after_roles}")
            if changes:
                actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_update, a)
                embed = self._emoji_embed("Emote updated", 0xFFD700, a, "\n".join(changes), actor)
                await self.bot_spam_channel.send(embed=embed)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Community(bot))
