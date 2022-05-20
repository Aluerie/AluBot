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
        irene_server = self.bot.get_guild(Sid.irene)
        patch_channel = irene_server.get_channel(Cid.suggestions)
        number = db.inc_value(db.g, Sid.irene, 'suggestion_num')
        title = f'Suggestion #{number}'
        embed = Embed(color=Clr.prpl, title=title, description=text)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f'With love, {irene_server.me.display_name}')
        message = await patch_channel.send(embed=embed)
        await message.add_reaction('⬆️')
        await message.add_reaction('⬇️')
        suggestion_thread = await message.create_thread(name=title)
        await suggestion_thread.send(content='Here you can discuss current suggestion')
        em2 = Embed(color=Clr.prpl)
        em2.description = f'{ctx.author.mention}, sent your suggestion under #{number} into {patch_channel.mention}'
        await ctx.channel.send(embed=em2)


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
