from discord import AuditLogAction, Embed
from discord.ext import commands, tasks
from utils.var import *
from utils.format import inline_wordbyword_diff
from utils import database as db

import regex
from datetime import timezone, time


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stonerole_check.start()

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        irene_server = self.bot.get_guild(Sid.irene)
        member = irene_server.get_member(after.id)
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
        if after.guild is None or after.guild.id != Sid.irene:
            return
        if before.author.bot is True:  # and before is not None and after is not None or after.edited_at is None:
            return

        embed = Embed(colour=0x00BFFF)
        embed.description = inline_wordbyword_diff(before.content, after.content)
        embed.set_author(
            name=f'{after.author.display_name} edit in #{after.channel.name}',
            icon_url=after.author.display_avatar.url,
            url=after.jump_url)  # TODO: this link is not jumpable from mobile but we dont care, right ?
        await self.bot.get_channel(Cid.logs).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.guild.id != Sid.irene or msg.author.bot:
            return
        if regex.search(Rgx.bug_check, msg.content):
            return
        if msg.content.startswith('$'):
            return

        embed = Embed(colour=0xB22222)
        embed.description = msg.content
        embed.set_author(
            name=f'{msg.author.display_name}\'s del in #{msg.channel.name}', icon_url=msg.author.display_avatar.url)
        files = [await item.to_file() for item in msg.attachments]
        return await self.bot.get_channel(Cid.logs).send(embed=embed, files=files)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id != Sid.irene:
            return

        if before.premium_since is None and after.premium_since is not None:
            embed = Embed(colour=Clr.prpl)
            embed.set_author(name=before.display_name, icon_url=before.display_avatar.url)
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.title = f"{before.display_name} just boosted the server !"
            embed.description = '{0} {0} {0}'.format(Ems.PogChampPepe)
            await self.bot.get_channel(Cid.general).send(embed=embed)

        added_role = list(set(after.roles) - set(before.roles))
        if added_role and added_role[0].id not in Rid.ignored_for_logs:
            embed = Embed(colour=0x00ff7f)
            embed.description = f'**Role added:** {added_role[0].mention}'
            embed.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.get_channel(Cid.logs).send(embed=embed)

        removed_role = list(set(before.roles) - set(after.roles))
        if removed_role and removed_role[0].id not in Rid.ignored_for_logs:
            embed = Embed(colour=0x006400)
            embed.description = f'**Role removed:** {removed_role[0].mention}'
            embed.set_author(name=f'{after.display_name}\'s roles changed', icon_url=after.display_avatar.url)
            return await self.bot.get_channel(Cid.logs).send(embed=embed)

        if before.bot:
            return

        if before.nick != after.nick:  # Nickname changed
            if (before.nick is not None and before.nick.startswith('[MUTED')) \
                    or (after.nick is not None and after.nick.startswith('[MUTED')):
                return
            db.set_value(db.m, after.id, name=after.display_name)
            embed = Embed(colour=after.color)
            embed.title = f'User\'s server nickname was changed {Ems.PepoDetective}'
            embed.description = f'**Before:** {before.nick}\n**After:** {after.nick}'
            embed.set_author(name=before.name, icon_url=before.display_avatar.url)
            await self.bot.get_channel(Cid.bot_spam).send(embed=embed)

            irene_server = self.bot.get_guild(Sid.irene)
            stone_rl = irene_server.get_role(Rid.rolling_stone)
            if after.nick and 'Stone' in after.nick:
                embed = Embed(colour=Clr.prpl)
                embed.description = f'{after.mention} gets lucky {stone_rl.mention} role {Ems.PogChampPepe}'
                await self.bot.get_channel(Cid.bot_spam).send(embed=embed)
                await after.add_roles(stone_rl)
            else:
                await after.remove_roles(stone_rl)

    @tasks.loop(time=time(hour=12, minute=57, tzinfo=timezone.utc))
    async def stonerole_check(self):
        irene_server = self.bot.get_guild(Sid.irene)
        stone_rl = irene_server.get_role(Rid.rolling_stone)
        async for entry in irene_server.audit_logs(action=AuditLogAction.member_update):
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
    async def turn_emote_logs(self, ctx):
        """Turn emote logs on in this channel for this guild ;"""
        db.append_row(db.c, name='emote_logs', guildid=ctx.guild.id, channelid=ctx.channel.id)
        embed = Embed(colour=Clr.prpl, title='Emote logging is turned on')
        embed.description = 'Now I will log emote create/delete/rename actions in this channel. Go try it!'
        embed.set_footer(text=f'With love, {ctx.bot.user.display_name}')
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        def find_channel():
            with db.session_scope() as ses:
                for row in ses.query(db.c).filter_by(guildid=guild.id):
                    if row.name == 'emote_logs':
                        return self.bot.get_channel(row.channelid)
                return None

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
                if not emote.managed and guild.id == Sid.irene:
                    db.remove_row(db.e, emote.id)
                embed = Embed(colour=0xb22222)
                embed.title = f'`:{emote.name}:` emote removed'
                await set_author(emote, embed, AuditLogAction.emoji_delete)
                embed.description = f'[Image link]({emote.url})'
                embed.set_thumbnail(url=emote.url)
                await channel.send(embed=embed)
        # Add emote ###############################################################################
        elif diff_after != [] and diff_before == []:
            for emote in diff_after:
                embed = Embed(colour=0x00ff7f)
                embed.title = f'`:{emote.name}:` emote created'
                await set_author(emote, embed, AuditLogAction.emoji_create)
                embed.description = f'[Image link]({emote.url})'
                embed.set_thumbnail(url=emote.url)
                await channel.send(embed=embed)
                if not emote.managed and guild.id == Sid.irene:
                    db.add_row(db.e, emote.id, name=str(emote), animated=emote.animated)
                    msg = await channel.send('{0} {0} {0}'.format(str(emote)))
                    await msg.add_reaction(str(emote))
        # Renamed emote ###########################################################################
        else:
            diff_after_name = [x for x in after if x.name not in [x.name for x in before]]
            diff_before_name = [x for x in before if x.name not in [x.name for x in after]]
            for emote_after, emote_before in zip(diff_after_name, diff_before_name):
                if not emote_after.managed and guild.id == Sid.irene:
                    db.set_value(db.e, emote_after.id, name=str(emote_after))
                embed = Embed(colour=0x1e90ff)
                word_for_action = 'replaced by' if emote_after.managed else 'renamed into'
                embed.title = f'`:{emote_before.name}:` emote {word_for_action} `:{emote_after.name}:`'
                await set_author(emote_after, embed, AuditLogAction.emoji_update)
                embed.description = f'[Image link]({emote_after.url})'
                embed.set_thumbnail(url=emote_after.url)
                await channel.send(embed=embed)


from discord.ext.bridge import BridgeExtContext, BridgeApplicationContext
from discord.ext.commands import Context
from discord import ApplicationContext


class CommandLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ignored_users = [Uid.irene]

    async def on_cmd_work(self, ctx):
        if ctx.author.id in self.ignored_users:
            return
        embed = Embed(colour=ctx.author.colour)

        prefix = getattr(ctx, 'clean_prefix', '/')

        if isinstance(ctx, BridgeExtContext) or isinstance(ctx, Context):
            ch = ctx.channel
            jump_url = ctx.message.jump_url
        elif isinstance(ctx, BridgeApplicationContext) or isinstance(ctx, ApplicationContext):
            ch = ctx.interaction.channel
            msg = await ctx.interaction.original_message()
            jump_url = msg.jump_url
        else:
            ch = 'unknown'
            jump_url = ''

        embed.description = f'Used [{prefix}{ctx.command.qualified_name}]({jump_url}) in {ch.mention}'
        embed.set_author(icon_url=ctx.author.display_avatar.url, name=ctx.author.display_name)
        await self.bot.get_channel(Cid.logs).send(embed=embed)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await self.on_cmd_work(ctx)

    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        await self.on_cmd_work(ctx)


def setup(bot):
    bot.add_cog(Logging(bot))
    bot.add_cog(EmoteLogging(bot))
    bot.add_cog(CommandLogging(bot))
