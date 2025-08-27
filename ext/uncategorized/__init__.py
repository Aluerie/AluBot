from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .tts import TextToSpeech

if TYPE_CHECKING:
    from bot import AluBot


class Uncategorised(
    TextToSpeech,
    # emote=Emote.DankHatTooBig,
):
    """Let us learn together."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Uncategorised(bot))
