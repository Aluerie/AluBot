from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
import feedparser
from discord.ext import commands

from utils import AluCog, aluloop, const, links

if TYPE_CHECKING:
    from utils import AluBot


class Dota2Tweets(AluCog):
    """Dota 2 Tweets"""

    username_tweet_id_pattern = r'(?:.*/(\w+)/status/(\d+))'

    @discord.utils.cached_property
    def news_channel(self):
        channel = self.hideout.spam if self.bot.test else self.community.dota2tweets
        return channel

    @commands.Cog.listener('on_message')
    async def on_dota2_tweet(self, message: discord.Message):
        # Twitter API is dead thus I become a bad actor with very dirty tech
        # of reposting content from Nitter RSS.
        if message.channel.id != const.Channel.copy_dota_tweets:
            # not our channel
            return

        tweet_urls = []
        for e in message.embeds:
            m = re.match(self.username_tweet_id_pattern, str(e.url))
            if m:
                username = m.group(1)
                tweet_id = m.group(2)

                tweet_urls.append(f'https://fxtwitter.com/{username}/status/{tweet_id}')

        # send tweet urls if any
        if tweet_urls:
            msg = await self.news_channel.send('\n'.join(tweet_urls))
            await msg.publish()
            msg2 = await links.extra_send_fxtwitter_links(msg)
            if msg2:
                await msg2.publish()


class NitterRSS(AluCog):
    async def cog_load(self) -> None:
        self.nitter_rss_watcher.start()
        # query = 'SELECT last_dota_rss_link FROM botvars WHERE id=TRUE'
        # self.latest_news_link = await self.bot.pool.fetchval(query)

    async def cog_unload(self) -> None:
        self.nitter_rss_watcher.cancel()

    usernames = ['dota2', 'wykrhm']
    url = 'https://nitter.net/{}/rss/'

    @aluloop(count=1)
    async def nitter_rss_watcher(self):
        for username in self.usernames:
            print(username)
            url = self.url.format(username)

            print(url)
            async with self.bot.session.get(url) as resp:
                rss_text = await resp.read()

                print(rss_text)
                rss = feedparser.parse(rss_text)
                entry = rss[0]

                # print(entry)


async def setup(bot: AluBot):
    await bot.add_cog(Dota2Tweets(bot))
