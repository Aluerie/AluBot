from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from utils.const import Emote

from .feedback import FeedbackCog
from .help import AluHelpCog
from .other import OtherCog

if TYPE_CHECKING:
    from bot import AluBot


class Meta(AluHelpCog, OtherCog, FeedbackCog):
    """Commands-utilities related to Discord or the Bot itself."""

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Emote.FeelsDankManLostHisHat)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Meta(bot))
