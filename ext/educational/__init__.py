from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .dictionary import Dictionary
from .translation import Translations
from .wolfram import WolframAlpha

if TYPE_CHECKING:
    from bot import AluBot


class Educational(
    Translations,
    Dictionary,
    WolframAlpha,
    # emote=Emote.PepoG,
):
    """Let us learn together."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Educational(bot))
