from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import discord
import feedparser

from config import DOTA_NEWS_WEBHOOK, PINK_TEST_WEBHOOK
from utils import AluCog, aluloop, const

if TYPE_CHECKING:
    from utils import AluBot


class Dota2RSS(AluCog):
    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.url = 'https://store.steampowered.com/feeds/news/app/570/'
        self.latest_news_link: str = ''

    async def cog_load(self) -> None:
        self.rss_watcher.start()
        query = 'SELECT last_dota_rss_link FROM botvars WHERE id=TRUE'
        self.latest_news_link = await self.bot.pool.fetchval(query)

    async def cog_unload(self) -> None:
        self.rss_watcher.cancel()

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(
            url=PINK_TEST_WEBHOOK if self.bot.test else DOTA_NEWS_WEBHOOK,
            client=self.bot,
            session=self.bot.session,
            bot_token=self.bot.http.token,
        )

    @aluloop(seconds=30)
    async def rss_watcher(self):
        rss = feedparser.parse(self.url)
        entry = rss.entries[0]

        if entry.link == self.latest_news_link:
            # no new posts
            return

        url = entry.link
        self.latest_news_link = url
        title = entry.title

        msg = await self.news_webhook.send(content=f'**{entry.title}**\n{url}', wait=True)
        await msg.publish()

        # just checking how we are late
        dt = datetime.datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z').astimezone(datetime.UTC)
        e = discord.Embed(title=title, url=url, colour=const.MaterialPalette.purple(shade=600))
        e.description = f'Timedelta between `entry.published` and `msg.created_at` is\n```\n{msg.created_at - dt}```'
        await self.hideout.spam.send(embed=e)

        query = 'UPDATE botvars SET last_dota_rss_link=$1 WHERE id=TRUE'
        await self.bot.pool.execute(query, url)


async def setup(bot):
    await bot.add_cog(Dota2RSS(bot))
