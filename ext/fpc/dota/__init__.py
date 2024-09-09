from __future__ import annotations

from typing import TYPE_CHECKING, override

from utils import const

from .notifications import DotaFPCNotifications
from .settings import DotaFPCSettings

if TYPE_CHECKING:
    from bot import AluBot


class DotaFPC(
    DotaFPCNotifications,
    DotaFPCSettings,
    emote=const.Emote.DankLove,
    name="Dota 2 FPC",  # careful with this name since it's used in `database_management.py`
):
    """Dota 2 - __F__avourite __P__layer+__C__haracter combo notifications."""

    @override
    async def cog_load(self) -> None:
        await self.bot.initialize_dota_pulsefire_clients()
        await self.bot.initialize_dota()
        await self.bot.initialize_twitch()
        return await super().cog_load()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DotaFPC(bot))
