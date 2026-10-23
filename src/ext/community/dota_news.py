"""Dota News.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from config import env
from core import Cog

if TYPE_CHECKING:
    from core import AluBot


class DotaNews(Cog):
    """Dota News."""

    ####################################################################################################################
    # STEAM DB REPOSTING
    ####################################################################################################################

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        """Webhook to send Dota 2 News to."""
        webhook_url = env.WEBHOOK_DOTANEWS if not self.bot.test else env.WEBHOOK_SPAM
        return self.bot.webhook_from_url(webhook_url)

    DOTA_STEAM_DB_UPDATES_CHANNEL_ID = 873430376033452053

    @commands.Cog.listener("on_message")
    async def filter_steam_db_messages(self, message: discord.Message) -> None:
        """Filter SteamDB messages from uninteresting ones.

        That channel contains all kind of updates, but we are only interested in blogpost ones.

        Warning
        -------
        Reposting from steamDB resources is rude and copyright-tier bad.
        Please, think of other ways to implement this (e.g. ISteamNews/GetNewsForApp or RSS feed)
        """
        if message.channel.id != self.DOTA_STEAM_DB_UPDATES_CHANNEL_ID:
            return
        if "https://steamcommunity.com" not in message.content:
            return

        msg = await self.news_webhook.send(content=f"# {message.content}", wait=True)
        await msg.publish()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DotaNews(bot))
