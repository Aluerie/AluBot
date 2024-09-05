from __future__ import annotations

from typing import TYPE_CHECKING, override

from bot import AluCog, ExtCategory
from utils.const import Emote

if TYPE_CHECKING:
    from bot import AluContext

category = ExtCategory(
    name="Developer tools",
    emote=Emote.DankFix,
    description="Tools for developers only",
)


class DevBaseCog(AluCog, category=category):
    @override
    async def cog_check(self, ctx: AluContext) -> bool:
        return await self.bot.is_owner(ctx.author)
