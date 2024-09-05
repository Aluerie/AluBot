from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .._base import EducationalCog
from .dictionary import DictionaryCog
from .translation import TranslateCog

if TYPE_CHECKING:
    from bot import AluBot


class Languages(
    TranslateCog,
    DictionaryCog,
    EducationalCog,
    emote=Emote.bedNerdge,
):
    """Languages."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Languages(bot))
