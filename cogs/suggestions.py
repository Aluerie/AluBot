from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils.var import Ems, Sid, Cid, Clr

if TYPE_CHECKING:
    from utils.bot import AluBot


class Suggestions(commands.Cog):
    """Commands related to suggestions such as

    * setting up suggestion channel
    * making said suggestions
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.peepoWTF)

    @commands.hybrid_command(aliases=["suggestion"])
    @app_commands.describe(text='Suggestion text')
    async def suggest(self, ctx, *, text: str):
        """Suggest something for people to vote on in suggestion channel"""
        patch_channel = self.bot.get_channel(Cid.suggestions)

        query = """ UPDATE botinfo 
                    SET suggestion_num=botinfo.suggestion_num+1 
                    WHERE id=$1 
                    RETURNING suggestion_num;
                """
        number = await self.bot.pool.fetchval(query, Sid.alu)

        title = f'Suggestion #{number}'
        e = discord.Embed(color=Clr.prpl, title=title, description=text)
        e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        e.set_footer(text=f'With love, {ctx.guild.me.display_name}')
        msg = await patch_channel.send(embed=e)
        await msg.add_reaction('\N{UPWARDS BLACK ARROW}')
        await msg.add_reaction('\N{DOWNWARDS BLACK ARROW}')
        suggestion_thread = await msg.create_thread(name=title, auto_archive_duration=7 * 24 * 60)
        await suggestion_thread.send(
            'Here you can discuss current suggestion.\n '
            'Don\'t forget to upvote/downvote initial suggestion message with '
            '\N{UPWARDS BLACK ARROW} \N{DOWNWARDS BLACK ARROW} reactions.'
        )
        e2 = discord.Embed(color=Clr.prpl)
        e2.description = f'{ctx.author.mention}, sent your suggestion under #{number} into {patch_channel.mention}'
        await ctx.reply(embed=e2, ephemeral=True)


async def setup(bot: AluBot):
    await bot.add_cog(Suggestions(bot))
