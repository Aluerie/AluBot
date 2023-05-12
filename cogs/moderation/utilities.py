from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import AluCog, const
from utils.checks import is_owner

if TYPE_CHECKING:
    from utils import AluContext


class ModUtilitiesCog(AluCog):
    @is_owner()
    @commands.command()
    async def spam_chat(self, ctx: AluContext):
        '''Let the bot to spam the chat in case you want
        to move some bad messages out of sight,
        but not clear/delete them.
        '''
        content = '\n'.join([const.Emote.DankHatTooBig for _ in range(20)])
        await ctx.send(content=content)


async def setup(bot):
    await bot.add_cog(ModUtilitiesCog(bot))
