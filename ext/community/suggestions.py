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
    """Suggestions."""

    @commands.Cog.listener(name="on_thread_create")
    async def pin_suggestion_topic(self, thread: discord.Thread) -> None:
        """Listener that pins suggestion message and sends a small reminder of rules."""
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
        embed = (
            discord.Embed(
                colour=const.Colour.prpl,
                title=f"Suggestion #{suggestion_num}",
            )
            .add_field(
                name="Hey chat, don't forget to \n",
                value=(
                    f"* upvote the pinned message with {const.Emote.DankApprove} reaction "
                    "if you like the suggestion and want it to be approved\n"
                    "* or downvote it with \N{CROSS MARK} if you really dislike the proposition.\n\n"
                    "OP, please, don't forget to use proper tags and provide as much info as needed, "
                    "i.e. 7tv link/gif file for a new emote suggestion."
                ),
            )
            .set_footer(text="Chat, please, discuss the suggestion in this thread.")
        )
        try:
            await thread.send(embed=embed)
        except discord.Forbidden as error:
            # Race condition with Discord
            if error.code == 40058:
                await asyncio.sleep(2)
                await thread.send(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Suggestions(bot))
