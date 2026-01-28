from __future__ import annotations

from typing import TYPE_CHECKING

from utils import const

from .feedback import FeedbackCog
from .help import AluHelpCog
from .other import OtherCog

if TYPE_CHECKING:
    from bot import AluBot


class Meta(
    FeedbackCog,
    AluHelpCog,
    OtherCog,
    # emote=const.Emote.DankLove,
    # name="Meta",
):
    """Meta."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Meta(bot))
