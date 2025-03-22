from __future__ import annotations

from typing import TYPE_CHECKING, override

from .notifications import DotaFPCNotifications
from .settings import DotaFPCSettings
from .twitch_renames import FPCDatabaseManagement

if TYPE_CHECKING:
    from bot import AluBot

__all__ = ("DotaFPC",)


class DotaFPC(
    DotaFPCNotifications,
    DotaFPCSettings,
    FPCDatabaseManagement,
    name="Dota 2 FPC",
):
    """Dota 2 - __F__avourite __P__layer+__C__haracter combo notifications."""

    @override
    async def cog_load(self) -> None:
        self.bot.instantiate_dota()
        await self.bot.instantiate_twitch()
        await super().cog_load()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DotaFPC(bot))
