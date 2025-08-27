from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .reminders import Reminders
from .timezone import TimezoneSettings

if TYPE_CHECKING:
    from bot import AluBot


class Remembrances(
    Reminders,
    TimezoneSettings,
    name="Reminders",
    # emote=Emote.peepoBusiness,
):
    """Remind yourself of something important.

    Make the bot ping you when it matters.
    """


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Remembrances(bot))
