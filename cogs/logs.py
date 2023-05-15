from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import discord
import regex
from discord.ext import commands, tasks

from utils import AluCog, const
from utils.formats import inline_word_by_word_diff

if TYPE_CHECKING:
    from utils import AluBot


class Logging(AluCog):
    async def cog_load(self) -> None:
        self.rolling_stones_check.start()

    async def cog_unload(self) -> None:
        self.rolling_stones_check.cancel()

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        member = self.bot.community.guild.get_member(after.id)
        if member is None:
            return
        e = discord.Embed(colour=member.colour)
        e.set_author(name=member.display_name, icon_url=before.display_avatar.url)
        if before.avatar != after.avatar:
            e.title = f'User\'s avatar was changed {const.Emote.PepoDetective}'
            e.description = '**Before:**  thumbnail to the right\n**After:** image below'
            e.set_thumbnail(url=before.display_avatar.url)
            e.set_image(url=after.display_avatar.url)
        elif before.name != after.name:
            e.title = f'User\'s global name was changed {const.Emote.PepoDetective}'
            e.description = f'**Before:** {before.name}\n**After:** {after.name}'
        elif before.discriminator != after.discriminator:
            e.title = f'User\'s discriminator was changed {const.Emote.PepoDetective}'
            e.description = f'**Before:** {before.discriminator}\n**After:** {after.discriminator}'
        return await self.bot.community.bot_spam.send(embed=e)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.guild is None or after.guild.id != const.Guild.community:
            return
        if before.author.bot is True:
            return
        if before.content == after.content:  # most likely some link embed link action
            return

        channel: discord.abc.GuildChannel = after.channel  # type: ignore
        e = discord.Embed(description=inline_word_by_word_diff(before.content, after.content), colour=0x00BFFF)
        e.set_author(
            name=f'{after.author.display_name} edit in #{channel.name}',
            icon_url=after.author.display_avatar.url,
            url=after.jump_url,  # TODO: this link is not jumpable from mobile but we dont care, right ?
        )
        await self.community.logs.send(embed=e)

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        if msg.author.bot or (msg.guild and msg.guild.id != const.Guild.community):
            return
        if regex.search(const.Rgx.bug_check, msg.content):  # bug_check
            return
        if msg.content.startswith('$'):
            return

        e = discord.Embed(description=msg.content, colour=0xB22222)
        e.set_author(
            name=f'{msg.author.display_name}\'s del in #{msg.channel.name}', icon_url=msg.author.display_avatar.url
        )
        files = [await item.to_file() for item in msg.attachments]
        return await self.bot.community.logs.send(embed=e, files=files)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
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

        if before.bot:
            return

        if before.nick != after.nick:  # Nickname changed
            if (before.nick is not None and before.nick.startswith('[AFK')) or (
                after.nick is not None and after.nick.startswith('[AFK')
            ):
                return

            query = 'UPDATE users SET name=$1 WHERE id=$2'
            await self.bot.pool.execute(query, after.display_name, after.id)
            e = discord.Embed(title=f'User\'s server nickname was changed {const.Emote.PepoDetective}', colour=after.color)
            e.description = f'**Before:** {before.nick}\n**After:** {after.nick}'
            e.set_author(name=before.name, icon_url=before.display_avatar.url)
            await self.bot.community.bot_spam.send(embed=e)

            stone_rl = self.bot.community.rolling_stone_role
            if after.nick and 'Stone' in after.nick:
                e = discord.Embed(colour=const.Colour.prpl())
                e.description = f'{after.mention} gets lucky {stone_rl.mention} role {const.Emote.PogChampPepe}'
                await self.bot.community.bot_spam.send(embed=e)
                await after.add_roles(stone_rl)
            else:
                await after.remove_roles(stone_rl)

    @tasks.loop(time=datetime.time(hour=12, minute=57, tzinfo=datetime.timezone.utc))
    async def rolling_stones_check(self):
        guild = self.bot.community.guild
        stone_rl = self.bot.community.rolling_stone_role

        async for entry in guild.audit_logs(action=discord.AuditLogAction.member_update):
            target: discord.Member = entry.target  # type: ignore
            if stone_rl in target.roles:
                return

            if 'Stone' in target.display_name:
                e = discord.Embed(
                    colour=stone_rl.colour,
                    description=f'{target.mention} gets lucky {stone_rl.mention} role {const.Emote.PogChampPepe}',
                )
                await self.bot.community.bot_spam.send(embed=e)
                await target.add_roles(stone_rl)
            else:
                await target.remove_roles(stone_rl)

    @rolling_stones_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class CommandLogging(AluCog):
    ignored_users = [const.User.alu]
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
    await bot.add_cog(Logging(bot))
    await bot.add_cog(CommandLogging(bot))
