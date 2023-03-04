from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot

DOTA_NEWS_CHANNEL = 724986688589267015


class DotaNewsBase(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def news_channel(self) -> discord.TextChannel:
        return self.bot.get_channel(DOTA_NEWS_CHANNEL)  # type: ignore # known announcement channel ID
