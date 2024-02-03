from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .._base import EducationalCog
from .wolfram import WolframAlphaCog

if TYPE_CHECKING:
    from bot import AluBot


class Mathematics(
    WolframAlphaCog,
    EducationalCog,
    emote=Emote.bedNerdge,
):
    """Mathematics."""


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Mathematics(bot))
