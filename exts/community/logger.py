from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import discord
import re
from discord.ext import commands, tasks

from utils import const
from utils.formats import inline_word_by_word_diff

from ._base import CommunityCog

if TYPE_CHECKING:
    from utils import AluBot


class CommunityMemberLogging(CommunityCog):
    async def cog_load(self) -> None:
        self.rolling_stones_check.start()

    async def cog_unload(self) -> None:
        self.rolling_stones_check.cancel()

    def base_embed(self, member: discord.Member) -> discord.Embed:
        return discord.Embed(colour=member.colour).set_author(name=str(member), icon_url=member.display_avatar.url)

    def verb_word(self, before: Any, after: Any) -> str:
        # TODO: make global func out of it because we use it in many files it feels like.
        if before is None and after:
            return 'set'
        if before and after is None:
            return 'removed'
        else:
            return 'changed'

    def before_after_embed(
        self,
        member: discord.Member,
        attribute_locale: str,
        before_field: str | None,
        after_field: str | None,
    ) -> discord.Embed:
        """
        Gives Before/After embed to send later for logger purposes

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
        ----------
        Embed to send for logger purposes
        """
        e = self.base_embed(member)
        e.description = (
            f'{member.mention}\'s {attribute_locale} was {self.verb_word(before_field, after_field)} '
            f'{const.Emote.PepoDetective}\n'
        )
        e.add_field(name='Before', value=discord.utils.escape_markdown(before_field) if before_field else "`...`")
        e.add_field(name='After', value=discord.utils.escape_markdown(after_field) if after_field else "`...`")
        return e

    @commands.Cog.listener('on_user_update')
    async def logger_on_user_update(self, before: discord.User, after: discord.User):
        # if self.community.guild.id not in before.mutual_guilds:
        #     return
        member = self.community.guild.get_member(after.id)
        if member is None:
            return

        # 99.99% of this event triggers on lonely changes so only one embed will be posted at a time
        # but docs say that multiple changes are possible at the same time so let's still count for it
        embeds: list[discord.Embed] = []

        if before.name != after.name:
            e = self.before_after_embed(member, 'username', before.name, after.name)
            embeds.append(e)
        elif before.discriminator != after.discriminator:
            e = self.before_after_embed(member, 'discriminator', before.discriminator, after.discriminator)
            embeds.append(e)
        elif before.global_name != after.global_name:
            e = self.before_after_embed(member, 'global display name', before.global_name, after.global_name)
            embeds.append(e)
        elif before.avatar != after.avatar:
            # TODO: maybe invite logic for default avatar as in removed/set from zero
            # like duckbot, even tho it's already clear enough
            e = self.before_after_embed(member, 'avatar', 'Thumbnail to the right', 'Image below')
            e.set_thumbnail(url=before.display_avatar.url)
            e.set_image(url=after.display_avatar.url)
            embeds.append(e)
        else:
            # Just for interest if it actually triggers for something else one future day
            # let's compare before and after by their attributes
            b = before.__dict__
            a = after.__dict__
            changes = [attr for attr in b if b[attr] != a[attr]]
            extra_e = self.base_embed(member)
            for attr in changes:
                # TODO: this will fail if 25+ fields
                value = f'**Before**: {getattr(before, attr)}\n**After**: {getattr(after, attr)}'
                extra_e.add_field(name=f'`{attr}`', value=value)
            extra_e.set_footer(text=f'{before.id}')
            await self.hideout.spam.send(embed=extra_e)

        # TODO: it will fail if there is more than 10 things
        await self.community.bot_spam.send(embeds=embeds)

    @commands.Cog.listener('on_member_update')
    async def logger_member_roles_update(self, before: discord.Member, after: discord.Member):
        if before.guild.id != const.Guild.community:
            return

        added_role = list(set(after.roles) - set(before.roles))
        if added_role and added_role[0].id not in const.IGNORED_FOR_LOGS:
            e = discord.Embed(description=f'**Role added:** {added_role[0].mention}', colour=0x00FF7F)
            e.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.community.logs.send(embed=e)

        removed_role = list(set(before.roles) - set(after.roles))
        if removed_role and removed_role[0].id not in const.IGNORED_FOR_LOGS:
            e = discord.Embed(description=f'**Role removed:** {removed_role[0].mention}', colour=0x006400)
            e.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.community.logs.send(embed=e)

    async def rolling_stones_role_check(self, after: discord.Member):
        rolling_stones_role = self.community.rolling_stone_role
        if after.nick and 'Stone' in after.nick:
            e = discord.Embed(colour=rolling_stones_role.colour)
            e.description = f'{after.mention} gets lucky {rolling_stones_role.mention} role {const.Emote.PogChampPepe}'
            await self.bot.community.bot_spam.send(embed=e)
            await after.add_roles(rolling_stones_role)
        else:
            await after.remove_roles(rolling_stones_role)

    @commands.Cog.listener('on_member_update')
    async def logger_member_nickname_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return

        if before.nick != after.nick:
            query = 'UPDATE users SET name=$1 WHERE id=$2'
            await self.bot.pool.execute(query, after.display_name, after.id)

            e = self.before_after_embed(after, 'server nickname', before.nick, after.nick)
            await self.bot.community.bot_spam.send(embed=e)

            # ROLLING STONES CHECK
            await self.rolling_stones_role_check(after)

    @tasks.loop(time=datetime.time(hour=12, minute=57, tzinfo=datetime.timezone.utc))
    async def rolling_stones_check(self):
        guild = self.bot.community.guild

        async for entry in guild.audit_logs(action=discord.AuditLogAction.member_update):
            target: discord.Member = entry.target  # type: ignore
            await self.rolling_stones_role_check(target)

    @rolling_stones_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class CommunityMessageLogging(CommunityCog):
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.guild is None or after.guild.id != const.Guild.community:
            return
        if before.author.bot is True:
            return
        if before.content == after.content:  # most likely some link embed link action
            return

        channel: discord.abc.GuildChannel = after.channel  # type: ignore # it's secured to be .community channel
        e = discord.Embed(colour=0x00BFFF)
        msg = f'{after.author.display_name} edit in #{channel.name}'
        e.set_author(name=msg, icon_url=after.author.display_avatar.url, url=after.jump_url)
        # TODO: if discord ever makes author field jumpable from mobile then remove [Jump Link] from below
        # TODO: inline word by word doesn't really work well on emote changes too
        # for example if before is peepoComfy and after is dankComfy then it wont be obvious in the embed result
        # since discord formats emotes first.
        e.description = f'[**Jump link**]({after.jump_url}) {inline_word_by_word_diff(before.content, after.content)}'
        await self.community.logs.send(embed=e)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or (message.guild and message.guild.id != const.Guild.community):
            return
        if re.search(const.Rgx.bug_check, message.content):  # bug_check
            return
        if message.content.startswith('$'):
            return

        channel: discord.abc.GuildChannel = message.channel  # type: ignore # it's secured to be .community channel
        e = discord.Embed(description=message.content, colour=0xB22222)
        msg = f'{message.author.display_name}\'s del in #{channel}'
        e.set_author(name=msg, icon_url=message.author.display_avatar.url)
        files = [await item.to_file() for item in message.attachments]
        return await self.bot.community.logs.send(embed=e, files=files)


class CommunityCommandLogging(CommunityCog):
    ignored_users = [const.User.aluerie]
    included_guilds = [const.Guild.community]

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        assert ctx.command

        if not ctx.guild or ctx.guild.id not in self.included_guilds or ctx.author.id in self.ignored_users:
            return

        cmd_kwargs = ' '.join([f'{k}: {v}' for k, v in ctx.kwargs.items()])
        if ctx.interaction:
            try:
                jump_url = (await ctx.interaction.original_response()).jump_url
            except discord.NotFound:
                jump_url = None
            cmd_text = f'/{ctx.command.qualified_name}'
        else:
            jump_url = ctx.message.jump_url
            cmd_text = ctx.message.content

        e = discord.Embed(description=f'{cmd_text}\n{cmd_kwargs}', colour=ctx.author.colour)
        if isinstance(ctx.channel, discord.DMChannel):
            channel_name = 'DMs'
        else:
            channel_name = getattr(ctx.channel, 'name', 'somewhere \N{THINKING FACE}')

        msg = f'{ctx.author.display_name} used command in {channel_name}'
        e.set_author(icon_url=ctx.author.display_avatar.url, name=msg, url=jump_url)
        await self.bot.community.logs.send(embed=e)


async def setup(bot: AluBot):
    for c in (CommunityMemberLogging, CommunityMessageLogging, CommunityCommandLogging):
        await bot.add_cog(c(bot))
