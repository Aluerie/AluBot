from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import AluCog, const, links

if TYPE_CHECKING:
    from utils import AluBot


class Dota2Tweets(AluCog):
    """Dota 2 Tweets"""

    username_tweet_id_pattern = r'(?:.*/(\w+)/status/(\d+))'

    @commands.Cog.listener('on_message')
    async def on_dota2_tweet(self, message: discord.Message):
        # Twitter API is dead thus I become a bad actor with very dirty tech
        # of reposting content from Nitter RSS.
        if message.channel.id != const.Channel.copy_dota_tweets:
            # not our channel
            return

        for e in message.embeds:
            m = re.match(self.username_tweet_id_pattern, str(e.url))
            if m:
                username = m.group(1)
                tweet_id = m.group(2)

                tweet_url = f'https://fxtwitter.com/{username}/status/{tweet_id}'

                msg = await self.community.dota2tweets.send(tweet_url)
                await msg.publish()
                msg2 = await links.extra_send_fxtwitter_links(msg)
                if msg2:
                    await msg2.publish()


async def setup(bot: AluBot):
    await bot.add_cog(Dota2Tweets(bot))
