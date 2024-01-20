"""
This cog is just rude reposting from steamdb resources. 

Unfortunately, I'm clueless about how to get the info from steam itself
And following announcement channels in steamdb discord is not a solution 
because I only need ~1/10 of messages they post in here.

If this ever becomes a problem or my bot becomes big t
hen I will have to rewrite this cog.

But for now I just repost messages I'm interested it to only my channel. 
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from config import DOTA_NEWS_WEBHOOK, TEST_SPAM_PINK_WEBHOOK
from utils import AluCog, const

if TYPE_CHECKING:
    from bot import AluBot


class SteamDB(AluCog):
    def cog_load(self) -> None:
        self.bot.initialize_github()

    @property
    def news_channel(self) -> discord.TextChannel:
        return self.community.dota_news

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(
            url=TEST_SPAM_PINK_WEBHOOK if self.bot.test else DOTA_NEWS_WEBHOOK,
            client=self.bot,
            session=self.bot.session,
            bot_token=self.bot.http.token,
        )

    # this is a bit shady since I just blatantly copy their messages
    # but Idk, I tried fetching Dota 2 news via different kinds of RSS
    # and my attempts were always 1-2 minutes later than steamdb
    # So until I find a better way or just ask them.
    @commands.Cog.listener("on_message")
    async def filter_steamdb_messages(self, message: discord.Message):
        if message.channel.id == const.Channel.dota_info:
            if "https://steamcommunity.com" in message.content:
                msg = await self.news_webhook.send(content=message.content, wait=True)
                await msg.publish()


async def setup(bot: AluBot):
    await bot.add_cog(SteamDB(bot))
