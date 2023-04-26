from __future__ import annotations

from typing import TYPE_CHECKING

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluContext


class ManagementBaseCog(AluCog):
    # if I ever forget to put @is_owner()
    # note that we still should put @is_owner() bcs of $help command quirk
    async def cog_check(self, ctx: AluContext) -> bool:
        return await self.bot.is_owner(ctx.author)
