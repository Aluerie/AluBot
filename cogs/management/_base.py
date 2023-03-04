from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context


class ManagementBase(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    # if I ever forget to put @is_owner()
    # note that we still should put @is_owner() bcs of $help command quirk
    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)
