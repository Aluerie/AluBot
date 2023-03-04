from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot

LOL_NEWS_CHANNEL = 724993871662022766


class LoLNewsBase(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def news_channel(self) -> discord.TextChannel:
        return self.bot.get_channel(LOL_NEWS_CHANNEL)  # type: ignore # known announcement channel ID
