from __future__ import annotations

import asyncio
import platform
from typing import TYPE_CHECKING

import tweepy.asynchronous
from discord.ext import tasks

from config import TWITTER_BEARER_TOKEN
from utils import AluCog, aluloop

if TYPE_CHECKING:
    from utils import AluBot

import logging

logger = logging.getLogger(__name__)


followed_array = [
    44680622,  # wykrhm
    176507184,  # dota2
    17388199,  # icefrog
    1272226371109031937,  # YAluerie
    1156653746702565382,  # dota2ti
]


class MyAsyncStreamingClient(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, bot: AluBot, bearer_token):
        super().__init__(
            bearer_token,
            #  wait_on_rate_limit=True
        )
        self.bot: AluBot = bot

    async def on_response(self, response: tweepy.StreamResponse):
        #  print('response', response)
        tweet = response.data
        try:
            username = response.includes['users'][0].username
        except KeyError:  # lazy, we probably should do separate on_includes or separate on_errors
            return

        #  print(tweet.id, tweet.author_id, tweet.in_reply_to_user_id)
        #  print(tweet.data)
        if tweet.in_reply_to_user_id is not None:
            return

        channel = self.bot.hideout.spam if tweet.author_id == 1272226371109031937 else self.bot.hideout.copy_dota_tweets
        await channel.send(content=f"https://twitter.com/{username}/status/{tweet.id}")

    async def on_request_error(self, status_code):
        msg = f"{self.bot.owner.mention} I'm stuck with twitter-stream {status_code}"
        await self.bot.hideout.spam.send(content=msg)
        self.disconnect()

    async def on_exception(self, exception):
        logger.error("Twitter Stream encountered an exception")
        await self.bot.send_traceback(exception, where='Exception in Twitter Async Stream')
        await asyncio.sleep(60)
        await new_stream(self.bot)

    async def initiate_stream(self):
        my_rule = tweepy.StreamRule(' OR '.join([f"from:{x}" for x in followed_array]))
        await self.add_rules(my_rule)
        self.filter(
            expansions='author_id', tweet_fields=['author_id', 'in_reply_to_user_id'], user_fields=['created_at']
        )


async def new_stream(bot: AluBot):
    myStream = MyAsyncStreamingClient(bot, TWITTER_BEARER_TOKEN)
    await myStream.initiate_stream()


class Twitter(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def cog_load(self) -> None:
        if platform.system() == 'Windows':
            # well, too bad twitter is blocked there without VPN
            # VPS is in fine country though
            return
        self.bot.ini_twitter()
        self.start_stream.start()

    def cog_unload(self) -> None:
        if platform.system() == 'Windows':
            return
        self.start_stream.cancel()

    @aluloop(count=1)
    async def start_stream(self):
        await new_stream(self.bot)

    @start_stream.error
    async def start_stream_error(self, error: BaseException):
        self.start_stream.restart()
        await self.hideout.spam.send(f'{error}')
        await self.bot.send_exception(error, from_where='Dota 2 Twitter Task')


async def setup(bot: AluBot):
    await bot.add_cog(Twitter(bot))
