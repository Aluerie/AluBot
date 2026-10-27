"""Logger.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import asyncio
import datetime as dt
import logging
from typing import TYPE_CHECKING, Final, override

import discord
from discord.ext import commands

from core import Cog
from shared import clock, globs
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core import Bot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Logger(Cog):
    """Logger."""

    BOT_SPAM_CHANNEL_ID: Final = const.ChannelId(724986090632642653)
    VOICE_CHAT_ROLE_ID = const.RoleId(1564454008905670797)

    @override
    async def cog_load(self) -> None:
        self.restart_clean_up.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.restart_clean_up.stop()
        await super().cog_unload()

    @discord.utils.cached_property
    def bot_spam_channel(self) -> discord.TextChannel:
        """Bot spam channel."""
        return self.bot.get_text_channel_or_test(self.BOT_SPAM_CHANNEL_ID)

    ####################################################################################################################
    # LOGGER
    ####################################################################################################################

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
            return None  # synced by an integration, so there's no "actor"

        cutoff = clock.utcnow() - dt.timedelta(seconds=15)
        for attempt in range(3):
            try:
                async for entry in guild.audit_logs(limit=10, action=action):
                    if entry.created_at < cutoff:
                        break
                    if entry.target is not None and entry.target.id == emoji.id:
                        return entry.user
            except discord.Forbidden:
                log.warning("Missing View Audit Log permission in %s", guild)
                return None
            if attempt < 2:
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

        for emoji_id in sorted(new.keys() - old.keys()):
            emoji = new[emoji_id]
            actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_create, emoji)
            embed = self._emoji_embed("Emote added", 0x00FF7F, emoji, f"`:{emoji.name}:`", actor)
            await self.bot_spam_channel.send(embed=embed)

        for emoji_id in sorted(old.keys() - new.keys()):
            emoji = old[emoji_id]
            actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_delete, emoji)
            embed = self._emoji_embed("Emote removed", 0xFF4500, emoji, f"`:{emoji.name}:`", actor)
            await self.bot_spam_channel.send(embed=embed)

        for emoji_id in sorted(old.keys() & new.keys()):
            b, a = old[emoji_id], new[emoji_id]
            changes: list[str] = []
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

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        """Log changes to a user's global profile to the bot spam channel (if they are a community member)."""
        guild = self.bot.get_guild(const.Guild.community)
        if guild is None or (member := guild.get_member(after.id)) is None:
            return

        embed = discord.Embed(
            title=f"User updated {const.Emoji.PepoDetective}",
            description=after.mention,
            color=member.color,
        ).set_author(name=str(after), icon_url=after.display_avatar.url)

        changed = False

        if before.name != after.name:
            changed = True
            embed.add_field(
                name="Username",
                value=f"`{before.name}` → `{after.name}`",
                inline=False,
            )

        if before.global_name != after.global_name:
            changed = True
            embed.add_field(
                name="Global Display name",
                value=f"`{before.global_name}` → `{after.global_name}`",
                inline=False,
            )

        if before.avatar != after.avatar:
            changed = True
            embed.add_field(
                name="Avatar",
                value="Before (thumbnail to the right) → After (image below)",
                inline=False,
            )
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)

        if not changed:
            return

        await self.bot_spam_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Log changes to a community member's guild profile to the bot spam channel."""
        if before.guild.id != const.Guild.community:
            return
        embed = discord.Embed(
            title=f"Member updated {const.Emoji.PepoDetective}",
            description=after.mention,
            color=after.color,
        ).set_author(name=str(after), icon_url=after.display_avatar.url)

        changed = False

        if before.nick != after.nick:
            changed = True
            embed.add_field(
                name="Nickname",
                value=f"`{before.nick}` → `{after.nick}`",
                inline=False,
            )

        # before_roles = set(before.roles)
        # after_roles = set(after.roles)
        # if added := after_roles - before_roles:
        #     changed = True
        #     embed.add_field(
        #         name="Roles added",
        #         value=", ".join(role.mention for role in sorted(added, reverse=True)),
        #         inline=False,
        #     )
        # if removed := before_roles - after_roles:
        #     changed = True
        #     embed.add_field(
        #         name="Roles removed",
        #         value=", ".join(role.mention for role in sorted(removed, reverse=True)),
        #         inline=False,
        #     )

        if before.timed_out_until != after.timed_out_until:
            changed = True
            if after.timed_out_until is None:
                timeout = "Timeout removed"
            else:
                timeout = f"Timed out until {clock.discord(after.timed_out_until)}"
            embed.add_field(name="Timeout", value=timeout, inline=False)

        if before.premium_since != after.premium_since:
            changed = True
            embed.add_field(
                name="Server boost",
                value="Started boosting" if after.premium_since else "Stopped boosting",
                inline=False,
            )

        if before.guild_avatar != after.guild_avatar:
            changed = True
            embed.add_field(
                name="Server avatar",
                value="Before (thumbnail to the right) → (After) (image below)",
                inline=False,
            )
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)

        if not changed:
            return

        await self.bot_spam_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Log community server changes to the bot spam channel."""
        if before.id != const.Guild.community:
            return

        embed = discord.Embed(
            title=f"Server updated {const.Emoji.PepoDetective}",
            color=0xF47FFF,
        ).set_author(name=after.name, icon_url=after.icon.url if after.icon is not None else None)

        changed = False

        if before.premium_tier != after.premium_tier:
            changed = True
            embed.add_field(
                name="Boost level",
                value=f"`Level {before.premium_tier}` → `Level {after.premium_tier}`",
                inline=False,
            )
            embed.add_field(
                name="Total boosts",
                value=str(after.premium_subscription_count),
                inline=False,
            )

        if not changed:
            return

        await self.bot_spam_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    # --- VOICE CHAT LOGGING -------------------------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Log voice state changes to the voice channel."""
        if member.guild.id != const.Guild.community:
            return

        role = self.VOICE_CHAT_ROLE_ID.object
        if before.channel is None and after.channel is not None:
            # joined the voice channel
            await member.add_roles(role)
            e = discord.Embed(color=0x00FF7F).set_author(
                name=f"{member.display_name} entered {after.channel.name}.",
                icon_url=member.display_avatar.url,
            )
            await after.channel.send(embed=e)
            return
        if before.channel is not None and after.channel is None:
            # quit the voice channel
            await member.remove_roles(role)
            e = discord.Embed(color=0x800000).set_author(
                name=f"{member.display_name} left {before.channel.name}.",
                icon_url=member.display_avatar.url,
            )
            await before.channel.send(embed=e)
            return
        if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            # changed voice channels
            e = discord.Embed(color=0x6495ED).set_author(
                name=f"{member.display_name} went from {before.channel.name} to {after.channel.name}.",
                icon_url=member.display_avatar.url,
            )
            await before.channel.send(embed=e)
            await after.channel.send(embed=e)
            return

    @loop(count=1, wait_for_ready=True)
    async def restart_clean_up(self) -> None:
        """Resync @Voice Chat Member role after a restart."""
        role = self.bot.get_role(const.Guild.community, self.VOICE_CHAT_ROLE_ID)

        # check if voice role has members who left the voice chat
        for member in role.members:
            if member.voice is None:
                await member.remove_roles(role)

        # vice versa: check if there are people in voice chat who don't have a role
        for voice_channel in role.guild.voice_channels:
            for member in voice_channel.members:
                await member.add_roles(role)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Logger(bot))
