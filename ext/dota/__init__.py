from __future__ import annotations

from typing import TYPE_CHECKING, override

from utils import const

from .bugtracker import BugTracker
from .fpc.notifications import DotaFPCNotifications
from .fpc.settings import DotaFPCSettings

if TYPE_CHECKING:
    from bot import AluBot


class DotaFPC(
    BugTracker,
    DotaFPCNotifications,
    DotaFPCSettings,
    emote=const.Emote.DankLove,
    name="Dota 2 FPC",  # careful with this name since it's used in `database_management.py`
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
