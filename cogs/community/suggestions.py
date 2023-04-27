from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import AluCog, Clr, Ems, Sid

if TYPE_CHECKING:
    from utils import AluBot


class Suggestions(AluCog, emote=Ems.peepoWTF):
    """Commands related to suggestions such as

    * setting up suggestion channel
    * making said suggestions
    """

    @app_commands.guilds(Sid.community)
    @app_commands.command()
    @app_commands.describe(text='Suggestion text')
    async def suggest(self, ntr: discord.Interaction, *, text: str):
        """Suggest something for people to vote on in suggestion channel"""
        channel = self.community.suggestions
        query = """ UPDATE botinfo 
                    SET suggestion_num=botinfo.suggestion_num+1 
                    WHERE id=$1 
                    RETURNING suggestion_num;
                """
        number = await self.bot.pool.fetchval(query, Sid.community)

        title = f'Suggestion #{number}'
        e = discord.Embed(color=Clr.prpl, title=title, description=text)
        e.set_author(name=ntr.user.display_name, icon_url=ntr.user.display_avatar.url)

        msg = await channel.send(embed=e)
        await msg.add_reaction('\N{UPWARDS BLACK ARROW}')
        await msg.add_reaction('\N{DOWNWARDS BLACK ARROW}')
        suggestion_thread = await msg.create_thread(name=title, auto_archive_duration=7 * 24 * 60)
        await suggestion_thread.send(
            'Here you can discuss current suggestion.\n '
            'Don\'t forget to upvote/downvote initial suggestion message with '
            '\N{UPWARDS BLACK ARROW} \N{DOWNWARDS BLACK ARROW} reactions.'
        )
        e2 = discord.Embed(color=Clr.prpl)
        e2.description = f'{ntr.user.mention}, sent your suggestion under #{number} into {channel.mention}'
        await ntr.response.send_message(embed=e2, ephemeral=True)


async def setup(bot: AluBot):
    await bot.add_cog(Suggestions(bot))
