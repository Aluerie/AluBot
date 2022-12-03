from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Embed, app_commands
from discord.ext import commands

from .utils.var import Ems, Sid, Cid, Clr, cmntn

if TYPE_CHECKING:
    from .utils.bot import AluBot


class Suggestions(commands.Cog):
    """Suggest something"""

    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.peepoWTF

    @commands.hybrid_command(
        name='suggest',
        description=f'Suggest something and people will vote on it in #patch_notes',
        help=f'Suggest something and people will vote on it in {cmntn(Cid.patch_notes)}',
        aliases=["suggestion"]
    )
    @app_commands.describe(text='Suggestion text')
    async def suggest(self, ctx, *, text: str):
        """Read above"""
        patch_channel = self.bot.get_channel(Cid.suggestions)

        query = """ UPDATE botinfo 
                    SET suggestion_num=botinfo.suggestion_num+1 
                    WHERE id=$1 
                    RETURNING suggestion_num;
                """
        number = await self.bot.pool.fetchval(query, Sid.alu)

        title = f'Suggestion #{number}'
        em = Embed(color=Clr.prpl, title=title, description=text)
        em.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        em.set_footer(text=f'With love, {ctx.guild.me.display_name}')
        msg = await patch_channel.send(embed=em)
        await msg.add_reaction('⬆️')
        await msg.add_reaction('⬇️')
        suggestion_thread = await msg.create_thread(name=title, auto_archive_duration=7*24*60)
        await suggestion_thread.send(
            'Here you can discuss current suggestion.\n '
            'Don\'t forget to upvote/downvote initial suggestion message with ⬆️⬇️reactions.'
        )
        em2 = Embed(color=Clr.prpl)
        em2.description = f'{ctx.author.mention}, sent your suggestion under #{number} into {patch_channel.mention}'
        await ctx.send(embed=em2, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
