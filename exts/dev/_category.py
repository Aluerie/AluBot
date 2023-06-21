from __future__ import annotations

from typing import TYPE_CHECKING

from utils import AluCog, ExtCategory, const

if TYPE_CHECKING:
    from utils import AluContext

category = ExtCategory(
    name='Developer tools',
    emote=const.Emote.DankFix,
    description='Tools for developers only',
)


class DevBaseCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)

    async def cog_check(self, ctx: AluContext) -> bool:
        return await self.bot.is_owner(ctx.author)
