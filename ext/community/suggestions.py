from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import const

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot


class Suggestions(CommunityCog, emote=const.Emote.peepoWTF):
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        if thread.parent_id != self.community.suggestions:
            return

        message = thread.get_partial_message(thread.id)
        try:
            await message.pin()
        except discord.HTTPException:
            pass

        query = """
            UPDATE botinfo
            SET suggestion_num=botinfo.suggestion_num+1
            WHERE id=$1
            RETURNING suggestion_num;
        """
        suggestion_num = await self.bot.pool.fetchval(query, const.Guild.community)
        e = discord.Embed(colour=const.Colour.blueviolet, title=f"Suggestion #{suggestion_num}")

        text = (
            f"* upvote the pinned message with {const.Emote.DankApprove} reaction "
            "if you like the suggestion and want it to be approved\n"
            "* or downvote it with \N{CROSS MARK} if you really dislike the proposition.\n\n"
            "OP, please, don't forget to use proper tags and provide as much info as needed, "
            "i.e. 7tv link/gif file for a new emote suggestion."
        )
        e.add_field(name="Hey chat, don't forget to \n", value=text)
        e.set_footer(text="Chat, please, discuss the suggestion in this thread.")
        try:
            await thread.send(embed=e)
        except discord.Forbidden as error:
            # Race condition with Discord
            if error.code == 40058:
                await asyncio.sleep(2)
                await thread.send(embed=e)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Suggestions(bot))
