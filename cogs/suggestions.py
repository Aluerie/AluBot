from discord import Embed, app_commands
from discord.ext import commands

from utils import database as db
from utils.var import *


class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Tools'

    @commands.hybrid_command(
        name='suggest',
        brief=Ems.slash,
        description=f'Suggest something and people will vote on it in #patch_notes',
        help=f'Suggest something and people will vote on it in {cmntn(Cid.patch_notes)}',
        aliases=["suggestion"]
    )
    @app_commands.describe(text='Suggestion text')
    async def suggest(self, ctx, *, text: str):
        """Read above"""
        guild = self.bot.get_guild(Sid.alu)
        patch_channel = guild.get_channel(Cid.suggestions)
        number = db.inc_value(db.b, Sid.alu, 'suggestion_num')
        title = f'Suggestion #{number}'
        em = Embed(
            color=Clr.prpl,
            title=title,
            description=text
        ).set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        ).set_footer(
            text=f'With love, {guild.me.display_name}'
        )
        msg = await patch_channel.send(embed=em)
        await msg.add_reaction('⬆️')
        await msg.add_reaction('⬇️')
        suggestion_thread = await msg.create_thread(name=title, auto_archive_duration=7*24*60)
        await suggestion_thread.send(
            content=
            'Here you can discuss current suggestion.\n '
            'Don\'t forget to upvote/downvote initial suggestion message with ⬆️⬇️reactions.'
        )
        em2 = Embed(
            color=Clr.prpl,
            description=f'{ctx.author.mention}, sent your suggestion under #{number} into {patch_channel.mention}'
        )
        await ctx.channel.send(embed=em2)


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
