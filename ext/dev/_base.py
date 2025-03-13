from __future__ import annotations

from typing import TYPE_CHECKING, override

from bot import AluCog

if TYPE_CHECKING:
    from bot import AluContext, AluInteraction


class BaseDevCog(AluCog):
    """A base Dev Cog class.

    Double-ensures that commands have owner-only check.
    """

    @override
    async def cog_check(self, ctx: AluContext) -> bool:
        return await self.bot.is_owner(ctx.author)

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        return await self.bot.is_owner(interaction.user)
