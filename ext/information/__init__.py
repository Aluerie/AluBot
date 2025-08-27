from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .discord_inspect import DiscordInspect
from .info import Info
from .schedule import Schedule

if TYPE_CHECKING:
    from bot import AluBot


class Information(
    DiscordInspect,
    Info,
    Schedule,
    # emote=Emote.PepoG,
):
    """Information."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Information(bot))
