from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot import AluCog
from config import config
from utils import const

if TYPE_CHECKING:
    from bot import AluBot


class SteamDB(AluCog):
    """Reposting dota 2 related announcements from SteamDB.

    Notes
    -----
    Yes, this is rude and copyright-bad reposting from steamdb resources.

    Unfortunately, I'm clueless about how to get the info from steam itself.
    Simply following steamDB announcement channels in their discord is not a solution
    because I only need ~1/50 of messages they post in here.

    If this ever becomes a problem or my bot becomes big then I will have to rewrite this cog.
    But for now I just repost messages I'm interested it to my private channel.

    My options for future:
    * RSS (but my attempts were always 1-2 minute behind SteamDB)
    * ??? idk
    """

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        """Webhook to send Dota 2 News to."""
        webhook_url = config["WEBHOOKS"]["DOTA_NEWS"] if not self.bot.test else config["WEBHOOKS"]["YEN_SPAM"]
        return self.bot.webhook_from_url(webhook_url)

    @commands.Cog.listener("on_message")
    async def filter_steamdb_messages(self, message: discord.Message) -> None:
        """Filter SteamDB messages from uninteresting ones.

        That channel contains all kind of updates, but we are only interested in blogpost ones.
        """
        if message.channel.id == const.Channel.dota_updates and "https://steamcommunity.com" in message.content:
            msg = await self.news_webhook.send(content=message.content, wait=True)
            await msg.publish()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(SteamDB(bot))
