from __future__ import annotations

import datetime
import inspect
import re
from typing import TYPE_CHECKING, Any, override

import discord
from discord.ext import commands

from bot import aluloop
from utils import const, formats

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, AluContext


class MemberLogging(CommunityCog):
    @override
    async def cog_load(self) -> None:
        self.nicknames_database_check.start()

    @override
    async def cog_unload(self) -> None:
        self.nicknames_database_check.cancel()

    def base_embed(self, member: discord.Member) -> discord.Embed:
        return discord.Embed(colour=member.colour).set_author(name=str(member), icon_url=member.display_avatar.url)

    def verb_word(self, before: Any, after: Any) -> str:
        # TODO: make global func out of it because we use it in many files it feels like.
        if before is None and after:
            return "set"
        if before and after is None:
            return "removed"
        else:
            return "changed"

    def before_after_embed(
        self,
        member: discord.Member,
        attribute_locale: str,
        before_field: str | None,
        after_field: str | None,
    ) -> discord.Embed:
        """Gives Before/After embed to send later for logger purposes.

        Parameters
        ----------
        member: discord.Member
            member for whom the embed is triggered for
        attribute_locale: str
            Name from Discord Settings page for changed @member's object attribute
        before_field: str | None
            Value of the said attribute before the triggered event
        after_field: str | None
            Value of the said attribute before the triggered event

        Returns
        -------
        Embed to send for logger purposes

        """
        e = self.base_embed(member)
        e.description = (
            f"{member.mention}'s {attribute_locale} was {self.verb_word(before_field, after_field)} "
            f"{const.Emote.PepoDetective}\n"
        )
        e.add_field(name="Before", value=discord.utils.escape_markdown(before_field) if before_field else "`...`")
        e.add_field(name="After", value=discord.utils.escape_markdown(after_field) if after_field else "`...`")
        return e

    @commands.Cog.listener("on_user_update")
    async def logger_on_user_update(self, before: discord.User, after: discord.User) -> None:
        # if self.community.guild.id not in before.mutual_guilds:
        #     return
        member = self.community.guild.get_member(after.id)
        if member is None:
            return

        # 99.99% of this event triggers on lonely changes so only one embed will be posted at a time
        # but docs say that multiple changes are possible at the same time so let's still count for it
        embeds: list[discord.Embed] = []

        if before.name != after.name:
            e = self.before_after_embed(member, "username", before.name, after.name)
            embeds.append(e)
        elif before.discriminator != after.discriminator:
            e = self.before_after_embed(member, "discriminator", before.discriminator, after.discriminator)
            embeds.append(e)
        elif before.global_name != after.global_name:
            e = self.before_after_embed(member, "global display name", before.global_name, after.global_name)
            embeds.append(e)
        elif before.avatar != after.avatar:
            # TODO: maybe invite logic for default avatar as in removed/set from zero
            # like duck bot, even tho it's already clear enough
            e = self.before_after_embed(member, "avatar", "Thumbnail to the right", "Image below")
            e.set_thumbnail(url=before.display_avatar.url)
            e.set_image(url=after.display_avatar.url)
            embeds.append(e)
        else:
            # Just for interest if it actually triggers for something else one future day
            # let's compare before and after by their attributes
            changes = [
                attr
                for attr in before.__dir__()
                if attr
                not in (
                    "system",  # sometimes it's missing resulting in "None != False"
                    "avatar_decoration",  # not interested
                    "avatar_decoration_sku_id",  # not interested
                )
                and not attr.startswith("_")
                and not inspect.ismethod(getattr(before, attr, None))
                and getattr(before, attr, None) != getattr(after, attr, None)
            ]
            if changes:
                extra_embed = self.base_embed(member)
                for attr in changes:
                    # TODO: this will fail if 25+ fields
                    value = f"**Before**: {getattr(before, attr, None)}\n**After**: {getattr(after, attr, None)}"
                    extra_embed.add_field(name=f"`{attr}`", value=value)
                extra_embed.set_footer(text=f"{before.id}")
                await self.bot.spam_webhook.send(embed=extra_embed)

        if embeds:
            # TODO: it will fail if there is more than 10 things
            await self.community.bot_spam.send(embeds=embeds)

    @commands.Cog.listener("on_member_update")
    async def logger_member_roles_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.guild.id != const.Guild.community:
            return

        added_role = list(set(after.roles) - set(before.roles))
        if added_role and added_role[0].id not in const.IGNORED_FOR_LOGS:
            e = discord.Embed(description=f"**Role added:** {added_role[0].mention}", colour=0x00FF7F)
            e.set_author(name=f"{after.display_name}'s roles changed", icon_url=after.display_avatar.url)
            await self.bot.community.logs.send(embed=e)
            return

        removed_role = list(set(before.roles) - set(after.roles))
        if removed_role and removed_role[0].id not in const.IGNORED_FOR_LOGS:
            e = discord.Embed(description=f"**Role removed:** {removed_role[0].mention}", colour=0x006400)
            e.set_author(name=f"{after.display_name}'s roles changed", icon_url=after.display_avatar.url)
            await self.bot.community.logs.send(embed=e)
            return

    ##############################################
    ###           NICKNAME CHANGES             ###
    ##############################################

    async def update_database_and_announce(self, member_after: discord.Member, nickname_before: str | None) -> None:
        query = "UPDATE community_members SET name=$1 WHERE id=$2"
        await self.bot.pool.execute(query, member_after.display_name, member_after.id)

        e = self.before_after_embed(member_after, "server nickname", nickname_before, member_after.nick)
        await self.bot.community.bot_spam.send(embed=e)

        # ROLLING STONES CHECK
        await self.rolling_stones_role_check(member_after)

    @commands.Cog.listener("on_member_update")
    async def logger_member_nickname_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.bot:
            return

        if before.nick != after.nick:
            await self.update_database_and_announce(member_after=after, nickname_before=before.nick)

    async def rolling_stones_role_check(self, after: discord.Member) -> None:
        """Parameters
        ----------
        after : discord.Member
            member whose nickname gonna be checked for rolling stones eligibility

        """
        rolling_stones_role = self.community.rolling_stone_role
        if not after.nick:
            return

        if "Stone" in after.nick and after not in rolling_stones_role.members:
            e = discord.Embed(colour=rolling_stones_role.colour)
            e.description = f"{after.mention} gets lucky {rolling_stones_role.mention} role {const.Emote.PogChampPepe}"
            await self.bot.community.bot_spam.send(embed=e)
            await after.add_roles(rolling_stones_role)
        elif "Stone" not in after.nick and after in rolling_stones_role.members:
            await after.remove_roles(rolling_stones_role)

    @aluloop(hours=6)
    async def nicknames_database_check(self) -> None:
        async def update_heartbeat(dt: datetime.datetime) -> None:
            query = "UPDATE bot_vars SET community_nickname_heartbeat=$1 WHERE id=$2"
            await self.bot.pool.execute(query, dt, True)

        if self.nicknames_database_check.current_loop == 0:
            # we need to check for nickname changes
            guild = self.bot.community.guild

            query = "SELECT community_nickname_heartbeat FROM bot_vars WHERE id=$1"
            heartbeat_dt: datetime.datetime = await self.bot.pool.fetchval(query, True)
            heartbeat_dt.replace(tzinfo=datetime.UTC)

            # get missed time.
            now = discord.utils.utcnow()
            suspect_targets = [
                entry.target
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_update, after=heartbeat_dt)
                if getattr(entry.after, "nick", None) != getattr(entry.before, "nick", None)
                and isinstance(entry.target, discord.Member)
            ]
            suspect_targets = list(dict.fromkeys(suspect_targets))  # remove duplicates

            for target in suspect_targets:
                query = "SELECT name FROM community_members WHERE id=$1"
                database_display_name = await self.bot.pool.fetchval(query, target.id)

                if database_display_name != target.display_name:
                    await self.update_database_and_announce(member_after=target, nickname_before=database_display_name)

            await update_heartbeat(now)
        else:
            await update_heartbeat(discord.utils.utcnow())


class MessageLogging(CommunityCog):
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.guild.id != const.Guild.community:
            return
        if before.author.bot:
            return
        if before.content == after.content:  # most likely some link embed link action
            return

        channel: discord.abc.GuildChannel = after.channel  # type: ignore # it's secured to be .community channel
        e = discord.Embed(colour=0x00BFFF)
        msg = f"{after.author.display_name} edit in #{channel.name}"
        e.set_author(name=msg, icon_url=after.author.display_avatar.url, url=after.jump_url)
        # TODO: if discord ever makes author field jumpable from mobile then remove [Jump Link] from below
        # TODO: inline word by word doesn't really work well on emote changes too
        # for example if before is peepoComfy and after is dankComfy then it wont be obvious in the embed result
        # since discord formats emotes first.
        e.description = (
            f"[**Jump link**]({after.jump_url}) {formats.inline_word_by_word_diff(before.content, after.content)}"
        )
        await self.community.logs.send(embed=e)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.author.bot or (message.guild and message.guild.id != const.Guild.community):
            return
        if re.search(const.Regex.IS_DELETED_BY_NQN, message.content):  # bug_check
            # todo: this leads to any messages with emotes being ignored.
            return
        if message.content.startswith("$"):
            return

        channel: discord.abc.GuildChannel = message.channel  # type: ignore # it's secured to be .community channel
        e = discord.Embed(description=message.content, colour=0xB22222)
        msg = f"{message.author.display_name}'s del in #{channel}"
        e.set_author(name=msg, icon_url=message.author.display_avatar.url)
        files = [await item.to_file() for item in message.attachments]
        await self.bot.community.logs.send(embed=e, files=files)


class CommandLogging(CommunityCog):
    ignored_users = (const.User.aluerie,)
    included_guilds = (const.Guild.community,)

    @commands.Cog.listener()
    async def on_command(self, ctx: AluContext) -> None:
        assert ctx.command

        if not ctx.guild or ctx.guild.id not in self.included_guilds or ctx.author.id in self.ignored_users:
            return

        cmd_kwargs = " ".join([f"{k}: {v}" for k, v in ctx.kwargs.items()])
        if ctx.interaction:
            try:
                jump_url = (await ctx.interaction.original_response()).jump_url
            except discord.NotFound:
                jump_url = None
            cmd_text = f"/{ctx.command.qualified_name}"
        else:
            jump_url = ctx.message.jump_url
            cmd_text = ctx.message.content

        e = discord.Embed(description=f"{cmd_text}\n{cmd_kwargs}", colour=ctx.author.colour)
        if isinstance(ctx.channel, discord.DMChannel):
            channel_name = "DMs"
        else:
            channel_name = getattr(ctx.channel, "name", "somewhere \N{THINKING FACE}")

        msg = f"{ctx.author.display_name} used command in {channel_name}"
        e.set_author(icon_url=ctx.author.display_avatar.url, name=msg, url=jump_url)
        await self.bot.community.logs.send(embed=e)


class VoiceChatMembersLogging(CommunityCog):
    @override
    async def cog_load(self) -> None:
        self.check_voice_members.start()

    @override
    async def cog_unload(self) -> None:
        self.check_voice_members.cancel()

    @commands.Cog.listener("on_voice_state_update")
    async def community_voice_chat_logging(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.guild.id != self.community.id:
            return

        voice_role = self.bot.community.voice_role
        if before.channel is None and after.channel is not None:
            # joined the voice channel
            await member.add_roles(voice_role)
            e = discord.Embed(color=0x00FF7F).set_author(
                name=f"{member.display_name} entered {after.channel.name}.", icon_url=member.display_avatar.url
            )
            await after.channel.send(embed=e)
            return
        if before.channel is not None and after.channel is None:
            # quit the voice channel
            await member.remove_roles(voice_role)
            e = discord.Embed(color=0x800000).set_author(
                name=f"{member.display_name} left {before.channel.name}.", icon_url=member.display_avatar.url
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

    @aluloop(count=1)
    async def check_voice_members(self) -> None:
        voice_role = self.community.voice_role

        # check if voice role has members who left the voice chat
        for member in voice_role.members:
            if member.voice is None:
                await member.remove_roles(voice_role)

        # vice versa: check if there are people in voice chat who don't have a role
        for voice_channel in self.community.guild.voice_channels:
            for member in voice_channel.members:
                await member.add_roles(voice_role)


async def setup(bot: AluBot) -> None:
    for c in (MemberLogging, MessageLogging, CommandLogging, VoiceChatMembersLogging):
        await bot.add_cog(c(bot))
