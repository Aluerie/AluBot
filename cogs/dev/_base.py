from __future__ import annotations

from typing import TYPE_CHECKING

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluContext


class DevBaseCog(AluCog):
    async def cog_check(self, ctx: AluContext) -> bool:
        return await self.bot.is_owner(ctx.author)
