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
    from . import Bot, Context, Interaction


__all__ = (
    "Cog",
    "DevCog",
)


class CogBase(commands.Cog):
    """AluCogBase.

    Attributes
    ----------
    bot: AluBot
        The bot instance.

    """

    def __init__(self, bot: Bot, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.bot: Bot = bot


class Cog(CogBase):
    """Cog."""


class DevCog(Cog):
    """Dev Cog class.

    Double-ensures that commands have owner-only check.
    """

    @override
    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)  # ty: ignore[invalid-argument-type]

    @override
    async def interaction_check(self, interaction: Interaction) -> bool:
        return await self.bot.is_owner(interaction.user)  # ty: ignore[invalid-argument-type]
