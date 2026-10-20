"""Cog.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from discord.ext import commands

if TYPE_CHECKING:
    from core import AluBot, AluContext, AluInteraction
    from utils import const


__all__ = (
    "AluCog",
    "AluDevCog",
)


class AluCogBase(commands.Cog):
    """AluCogBase.

    Attributes
    ----------
    bot: AluBot
        The bot instance.

    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.bot: AluBot = bot

    @property
    def community(self) -> const.CommunityGuild:
        """Shortcut to get Community Guild object."""
        return self.bot.community

    @property
    def hideout(self) -> const.HideoutGuild:
        """Shortcut to get Hideout Guild object."""
        return self.bot.hideout


class AluCog(AluCogBase):
    """AluCog."""


class AluDevCog(AluCog):
    """Alu Dev Cog class.

    Double-ensures that commands have owner-only check.
    """

    @override
    async def cog_check(self, ctx: AluContext) -> bool:  # ty: ignore[invalid-method-override]
        return await self.bot.is_owner(ctx.author)  # ty: ignore[invalid-argument-type]

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        return await self.bot.is_owner(interaction.user)  # ty: ignore[invalid-argument-type]
