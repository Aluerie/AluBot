from discord import Embed
from discord.ext import commands

from utils.checks import is_owner
from utils.var import *
from utils import database as db


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


async def setup(bot):
    await bot.add_cog(Prefix(bot))
