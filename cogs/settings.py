from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import AuditLogAction, Embed, TextChannel
from discord.ext import commands

from utils.checks import is_owner
from utils.var import *
from utils import database as db

if TYPE_CHECKING:
    pass


async def get_pre(bot, message):
    if message.guild is None:
        prefix = '$'
    else:
        prefix = db.get_value(db.ga, message.guild.id, 'prefix')
    return commands.when_mentioned_or(prefix, "/")(bot, message)


class Prefix(commands.Cog, name='Settings for the bot'):
    """
    Change bot's config for the server

    More to come.
    """
    def __init__(self, bot):
        self.bot = bot
        self.help_emote = Ems.PepoBeliever

    @is_owner()
    @commands.group()
    async def alubotprefix(self, ctx):
        """Get a prefix for this server ;"""
        if ctx.invoked_subcommand is None:
            prefix = db.get_value(db.ga, ctx.guild.id, 'prefix')
            em = Embed(
                colour=Clr.prpl,
                description=f'This server current prefix is {prefix}'
            ).set_footer(
                text='To change prefix use `alubotprefix set` command'
            )
            await ctx.reply(embed=em)

    @is_owner()
    @alubotprefix.command()
    async def set(self, ctx, *, arg):
        """Set new prefix for the server ;"""
        db.set_value(db.ga, ctx.guild.id, prefix=arg)
        self.bot.command_prefix = get_pre
        em = Embed(
            colour=Clr.prpl,
            description=f'Changed this server prefix to {arg}'
        )
        await ctx.reply(embed=em)

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


async def setup(bot):
    await bot.add_cog(Prefix(bot))
