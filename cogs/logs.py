from __future__ import annotations
from typing import TYPE_CHECKING

import datetime

import discord
from discord.ext import commands, tasks
import regex

from .utils.formats import inline_wordbyword_diff
from .utils.var import Sid, Ems, Cid, Rgx, Clr, Rid

if TYPE_CHECKING:
    from .utils.bot import AluBot


class Logging(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        self.stonerole_check.start()

    async def cog_unload(self) -> None:
        self.stonerole_check.cancel()

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        member = self.bot.get_guild(Sid.alu).get_member(after.id)
        if member is None:
            return
        e = discord.Embed(colour=member.colour)
        e.set_author(name=member.display_name, icon_url=before.display_avatar.url)
        if before.avatar != after.avatar:
            e.title = f'User\'s avatar was changed {Ems.PepoDetective}'
            e.description = '**Before:**  thumbnail to the right\n**After:** image below'
            e.set_thumbnail(url=before.display_avatar.url)
            e.set_image(url=after.display_avatar.url)
        elif before.name != after.name:
            e.title = f'User\'s global name was changed {Ems.PepoDetective}'
            e.description = f'**Before:** {before.name}\n**After:** {after.name}'
        elif before.discriminator != after.discriminator:
            e.title = f'User\'s discriminator was changed {Ems.PepoDetective}'
            e.description = f'**Before:** {before.discriminator}\n**After:** {after.discriminator}'
        return await self.bot.get_channel(Cid.bot_spam).send(embed=e)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.guild is None or after.guild.id != Sid.alu:
            return
        if before.author.bot is True:
            return
        if before.content == after.content:  # most likely some link embed link action
            return

        e = discord.Embed(description=inline_wordbyword_diff(before.content, after.content), colour=0x00BFFF)
        e.set_author(
            name=f'{after.author.display_name} edit in #{after.channel.name}',
            icon_url=after.author.display_avatar.url,
            url=after.jump_url  # TODO: this link is not jumpable from mobile but we dont care, right ?
        )
        await self.bot.get_channel(Cid.logs).send(embed=e)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.guild.id != Sid.alu or msg.author.bot:
            return
        if regex.search(Rgx.bug_check, msg.content):
            return
        if msg.content.startswith('$'):
            return

        e = discord.Embed(description=msg.content, colour=0xB22222)
        e.set_author(
            name=f'{msg.author.display_name}\'s del in #{msg.channel.name}',
            icon_url=msg.author.display_avatar.url
        )
        files = [await item.to_file() for item in msg.attachments]
        return await self.bot.get_channel(Cid.logs).send(embed=e, files=files)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id != Sid.alu:
            return

        if before.premium_since is None and after.premium_since is not None:
            e = discord.Embed(title=f"{before.display_name} just boosted the server !", colour=Clr.prpl)
            e. description = '{0} {0} {0}'.format(Ems.PogChampPepe)
            e.set_author(name=before.display_name, icon_url=before.display_avatar.url)
            e.set_thumbnail(url=before.display_avatar.url)
            for ch_id in [Cid.general, Cid.logs]:
                await self.bot.get_channel(ch_id).send(embed=e)

        added_role = list(set(after.roles) - set(before.roles))
        if added_role and added_role[0].id not in Rid.ignored_for_logs:
            e = discord.Embed(description=f'**Role added:** {added_role[0].mention}', colour=0x00ff7f)
            e.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.get_channel(Cid.logs).send(embed=e)

        removed_role = list(set(before.roles) - set(after.roles))
        if removed_role and removed_role[0].id not in Rid.ignored_for_logs:
            e = discord.Embed(description=f'**Role removed:** {removed_role[0].mention}', colour=0x006400)
            e.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.get_channel(Cid.logs).send(embed=e)

        if before.bot:
            return

        if before.nick != after.nick:  # Nickname changed
            if (before.nick is not None and before.nick.startswith('[AFK')) \
                    or (after.nick is not None and after.nick.startswith('[AFK')):
                return

            query = 'UPDATE users SET name=$1 WHERE id=$2'
            await self.bot.pool.execute(query, after.display_name, after.id)
            e = discord.Embed(title=f'User\'s server nickname was changed {Ems.PepoDetective}', colour=after.color)
            e.description = f'**Before:** {before.nick}\n**After:** {after.nick}'
            e.set_author(name=before.name, icon_url=before.display_avatar.url)
            await self.bot.get_channel(Cid.bot_spam).send(embed=e)

            guild = self.bot.get_guild(Sid.alu)
            stone_rl = guild.get_role(Rid.rolling_stone)
            if after.nick and 'Stone' in after.nick:
                e = discord.Embed(colour=Clr.prpl)
                e.description = f'{after.mention} gets lucky {stone_rl.mention} role {Ems.PogChampPepe}'
                await self.bot.get_channel(Cid.bot_spam).send(embed=e)
                await after.add_roles(stone_rl)
            else:
                await after.remove_roles(stone_rl)

    @tasks.loop(time=datetime.time(hour=12, minute=57, tzinfo=datetime.timezone.utc))
    async def stonerole_check(self):
        guild = self.bot.get_guild(Sid.alu)
        stone_rl = guild.get_role(Rid.rolling_stone)
        async for entry in guild.audit_logs(action=discord.AuditLogAction.member_update):
            if isinstance(entry.target, discord.User) or stone_rl in entry.target.roles:
                return
            if 'Stone' in entry.target.display_name:
                e = discord.Embed(
                    colour=stone_rl.colour,
                    description=f'{entry.target.mention} gets lucky {stone_rl.mention} role {Ems.PogChampPepe}'
                )
                await self.bot.get_channel(Cid.bot_spam).send(embed=e)
                await entry.target.add_roles(stone_rl)
            else:
                await entry.target.remove_roles(stone_rl)

    @stonerole_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class CommandLogging(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot

    ignored_users = []  # [Uid.alu]
    included_guilds = [Sid.alu]

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        if ctx.guild.id not in self.included_guilds or ctx.author.id in self.ignored_users:
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
        e.set_author(
            icon_url=ctx.author.display_avatar.url,
            name=f'{ctx.author.display_name} used command in {ctx.channel.name}',
            url=jump_url
        )
        await self.bot.get_channel(Cid.logs).send(embed=e)


async def setup(bot: AluBot):
    await bot.add_cog(Logging(bot))
    await bot.add_cog(CommandLogging(bot))
