from discord import Embed, option
from discord.ext import commands, bridge
from utils.var import *

from utils import database as db


class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Tools'

    @bridge.bridge_command(
        aliases=["suggestion"],
        description=f'Suggest something and people will vote on it in #patch_notes',
        help=f'Suggest something and people will vote on it in {cmntn(Cid.patch_notes)}',
        brief=Ems.slash
    )
    @option('text', desription='Suggestion text')
    async def suggest(self, ctx, *, text: str):
        """Read above"""
        irene_server = self.bot.get_guild(Sid.irene)
        patch_channel = irene_server.get_channel(Cid.patch_notes)
        number = db.inc_value(db.g, Sid.irene, 'suggestion_num')
        title = f'Suggestion #{number}'
        embed = Embed(color=Clr.prpl, title=title)
        embed.description = text
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f'With love, {irene_server.me.display_name}')
        message = await patch_channel.send(embed=embed)
        await message.add_reaction('⬆️')
        await message.add_reaction('⬇️')
        suggestion_thread = await message.create_thread(title)
        await suggestion_thread.send(content='Here you can discuss current suggestion')
        response = f'{ctx.author.mention}, sent your suggestion under #{number} into {patch_channel.mention}'
        embed2 = Embed(color=Clr.prpl)
        embed2.description = response
        await ctx.channel.respond(embed=embed2)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Suggestions(bot))
