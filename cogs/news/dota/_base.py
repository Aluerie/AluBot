from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot


class DotaNewsBase(commands.Cog):

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def news_channel(self) -> discord.TextChannel:
        # 724986688589267015*
        return self.bot.get_channel(1066379298363166791)  # type: ignore # known announcement channel ID

