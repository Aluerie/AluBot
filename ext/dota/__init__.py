from __future__ import annotations

from typing import TYPE_CHECKING

from utils import const

from .bugtracker import BugTracker

# from .fpc import DotaFPC
# from .profile import SteamDotaProfiles
from .steamdb import SteamDB

if TYPE_CHECKING:
    from bot import AluBot


class Dota(
    BugTracker,
    # DotaFPC,
    # SteamDotaProfiles,
    SteamDB,
    # emote=const.Emote.DankLove,
    name="Dota",
):
    """Dota 2 - __F__avourite __P__layer+__C__haracter combo notifications."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Dota(bot))
