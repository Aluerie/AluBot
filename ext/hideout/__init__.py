from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .moderation import HideoutModeration
from .personal import HideoutPersonal

if TYPE_CHECKING:
    from bot import AluBot


class Hideout(
    HideoutModeration,
    HideoutPersonal,
    emote=Emote.KURU,
    hidden=True,
):
    """Hideout Only commands."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Hideout(bot))
