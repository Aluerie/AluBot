from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import AuditLogAction, Embed, TextChannel
from discord.ext import commands, tasks
from utils.var import *
from utils.format import inline_wordbyword_diff
from utils import database as db

import regex
from datetime import timezone, time

if TYPE_CHECKING:
    pass


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stonerole_check.start()

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        member = self.bot.get_guild(Sid.alu).get_member(after.id)
        if member is None:
            return
        embed = Embed(colour=member.colour)
        embed.set_author(name=member.display_name, icon_url=before.display_avatar.url)
        if before.avatar != after.avatar:
            embed.title = f'User\'s avatar was changed {Ems.PepoDetective}'
            embed.description = '**Before:**  thumbnail to the right\n**After:** image below'
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)
        elif before.name != after.name:
            embed.title = f'User\'s global name was changed {Ems.PepoDetective}'
            embed.description = f'**Before:** {before.name}\n**After:** {after.name}'
        elif before.discriminator != after.discriminator:
            embed.title = f'User\'s discriminator was changed {Ems.PepoDetective}'
            embed.description = f'**Before:** {before.discriminator}\n**After:** {after.discriminator}'
        return await self.bot.get_channel(Cid.bot_spam).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.guild is None or after.guild.id != Sid.alu:
            return
        if before.author.bot is True:
            return
        if before.content == after.content:  # most likely some link embed link action
            return

        embed = Embed(colour=0x00BFFF, description=inline_wordbyword_diff(before.content, after.content))
        embed.set_author(
            name=f'{after.author.display_name} edit in #{after.channel.name}',
            icon_url=after.author.display_avatar.url,
            url=after.jump_url)  # TODO: this link is not jumpable from mobile but we dont care, right ?
        await self.bot.get_channel(Cid.logs).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.guild.id != Sid.alu or msg.author.bot:
            return
        if regex.search(Rgx.bug_check, msg.content):
            return
        if msg.content.startswith('$'):
            return

        em = Embed(
            colour=0xB22222,
            description=msg.content
        ).set_author(
            name=f'{msg.author.display_name}\'s del in #{msg.channel.name}',
            icon_url=msg.author.display_avatar.url
        )
        files = [await item.to_file() for item in msg.attachments]
        return await self.bot.get_channel(Cid.logs).send(embed=em, files=files)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id != Sid.alu:
            return

        if before.premium_since is None and after.premium_since is not None:
            em = Embed(colour=Clr.prpl, title=f"{before.display_name} just boosted the server !")
            em.set_author(name=before.display_name, icon_url=before.display_avatar.url)
            em.set_thumbnail(url=before.display_avatar.url)
            em.description = '{0} {0} {0}'.format(Ems.PogChampPepe)
            await self.bot.get_channel(Cid.general).send(embed=em)

        added_role = list(set(after.roles) - set(before.roles))
        if added_role and added_role[0].id not in Rid.ignored_for_logs:
            em = Embed(colour=0x00ff7f)
            em.description = f'**Role added:** {added_role[0].mention}'
            em.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.get_channel(Cid.logs).send(embed=em)

        removed_role = list(set(before.roles) - set(after.roles))
        if removed_role and removed_role[0].id not in Rid.ignored_for_logs:
            em = Embed(colour=0x006400)
            em.description = f'**Role removed:** {removed_role[0].mention}'
            em.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.get_channel(Cid.logs).send(embed=em)

        if before.bot:
            return

        if before.nick != after.nick:  # Nickname changed
            if (before.nick is not None and before.nick.startswith('[AFK')) \
                    or (after.nick is not None and after.nick.startswith('[AFK')):
                return
            db.set_value(db.m, after.id, name=after.display_name)
            em = Embed(colour=after.color)
            em.title = f'User\'s server nickname was changed {Ems.PepoDetective}'
            em.description = f'**Before:** {before.nick}\n**After:** {after.nick}'
            em.set_author(name=before.name, icon_url=before.display_avatar.url)
            await self.bot.get_channel(Cid.bot_spam).send(embed=em)

            guild = self.bot.get_guild(Sid.alu)
            stone_rl = guild.get_role(Rid.rolling_stone)
            if after.nick and 'Stone' in after.nick:
                em = Embed(colour=Clr.prpl)
                em.description = f'{after.mention} gets lucky {stone_rl.mention} role {Ems.PogChampPepe}'
                await self.bot.get_channel(Cid.bot_spam).send(embed=em)
                await after.add_roles(stone_rl)
            else:
                await after.remove_roles(stone_rl)

    @tasks.loop(time=time(hour=12, minute=57, tzinfo=timezone.utc))
    async def stonerole_check(self):
        guild = self.bot.get_guild(Sid.alu)
        stone_rl = guild.get_role(Rid.rolling_stone)
        async for entry in guild.audit_logs(action=AuditLogAction.member_update):
            if stone_rl in entry.target.roles:
                return
            if entry.target.nick and 'Stone' in entry.target.nick:
                embed = Embed(colour=stone_rl.colour)
                embed.description = f'{entry.target.mention} gets lucky {stone_rl.mention} role {Ems.PogChampPepe}'
                await self.bot.get_channel(Cid.bot_spam).send(embed=embed)
                await entry.target.add_roles(stone_rl)
            else:
                await entry.target.remove_roles(stone_rl)

    @stonerole_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class EmoteLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'AdminTools'

    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(view_audit_log=True)
    async def turn_emote_logs(self, ctx: commands.Context, channel: Optional[TextChannel] = None):
        """Turn emote logs on in this channel for this guild ;"""
        ch = channel or ctx.channel
        db.set_value(db.ga, ctx.guild.id, emote_logs_id=ch.id)

        embed = Embed(
            colour=Clr.prpl,
            title='Emote logging is turned on',
            description=f'Now I will log emote create/delete/rename actions in {ch.mention}. Go try it!'
        ).set_footer(
            text=f'With love, {ctx.guild.me.display_name}'
        ).set_thumbnail(
            url=ctx.guild.me.display_avatar.url
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        def find_channel():
            with db.session_scope() as ses:
                row = ses.query(db.ga).filter_by(id=guild.id).first()
                return self.bot.get_channel(row.emote_logs_id)

        if (channel := find_channel()) is None:
            return

        diff_after = [x for x in after if x not in before]
        diff_before = [x for x in before if x not in after]

        async def set_author(emotion, embedx, act):
            if emotion.managed:
                embedx.set_author(name='Tw.tv Sub integration', icon_url=Img.twitchtv)
                return
            else:
                async for entry in guild.audit_logs(action=act):
                    if entry.target.id == emotion.id:
                        embedx.set_author(name=entry.user.name, icon_url=entry.user.display_avatar.url)
                        return
        # Remove emote ###########################################################################
        if diff_after == [] and diff_before != []:
            for emote in diff_before:
                if not emote.managed and guild.id == Sid.alu:
                    db.remove_row(db.e, emote.id)
                embed = Embed(
                    colour=0xb22222,
                    title=f'`:{emote.name}:` emote removed',
                    description=f'[Image link]({emote.url})'
                ).set_thumbnail(url=emote.url)
                await set_author(emote, embed, AuditLogAction.emoji_delete)
                await channel.send(embed=embed)
        # Add emote ###############################################################################
        elif diff_after != [] and diff_before == []:
            for emote in diff_after:
                embed = Embed(
                    colour=0x00ff7f,
                    title=f'`:{emote.name}:` emote created',
                    description=f'[Image link]({emote.url})'
                ).set_thumbnail(url=emote.url)
                await set_author(emote, embed, AuditLogAction.emoji_create)
                await channel.send(embed=embed)
                if not emote.managed:
                    msg = await channel.send('{0} {0} {0}'.format(str(emote)))
                    await msg.add_reaction(str(emote))
                if guild.id == Sid.alu:
                    db.add_row(db.e, emote.id, name=str(emote), animated=emote.animated)
        # Renamed emote ###########################################################################
        else:
            diff_after_name = [x for x in after if x.name not in [x.name for x in before]]
            diff_before_name = [x for x in before if x.name not in [x.name for x in after]]
            for emote_after, emote_before in zip(diff_after_name, diff_before_name):
                if not emote_after.managed and guild.id == Sid.alu:
                    db.set_value(db.e, emote_after.id, name=str(emote_after))
                embed = Embed(
                    colour=0x1e90ff,
                    title=
                    f'`:{emote_before.name}:` emote '
                    f'{"replaced by" if emote_after.managed else "renamed into"} '
                    f'`:{emote_after.name}:`',
                    description=f'[Image link]({emote_after.url})',
                ).set_thumbnail(url=emote_after.url)
                await set_author(emote_after, embed, AuditLogAction.emoji_update)
                await channel.send(embed=embed)


class CommandLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ignored_users = [Uid.alu]
    included_guilds = [Sid.alu]

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        if ctx.guild.id not in self.included_guilds or ctx.author.id in self.ignored_users:
            return

        cmd_kwargs = ' '.join([f'{k}: {v}' for k, v in ctx.kwargs.items()])
        if ctx.interaction:
            jump_url = (await ctx.interaction.original_message()).jump_url
            cmd_text = f'/{ctx.command.qualified_name}'
        else:
            jump_url = ctx.message.jump_url
            cmd_text = ctx.message.content

        embed = Embed(
            colour=ctx.author.colour,
            description=f'{cmd_text}\n{cmd_kwargs}'
        ).set_author(
            icon_url=ctx.author.display_avatar.url,
            name=f'{ctx.author.display_name} used command in {ctx.channel.name}',
            url=jump_url
        )
        await self.bot.get_channel(Cid.logs).send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logging(bot))
    await bot.add_cog(EmoteLogging(bot))
    await bot.add_cog(CommandLogging(bot))
