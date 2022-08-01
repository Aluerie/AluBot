from __future__ import annotations
from typing import TYPE_CHECKING

from os import getenv
import re

import tweepy.asynchronous

from discord.ext import commands

from utils.imgtools import url_to_file
from utils.var import Cid, Uid, umntn

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot

# #################### WHILE TWITTER IS BANNED IN RUSSIA #####################################
# TODO: remove this when twitter is unbanned
import logging
logger = logging.getLogger('tweepy')
#logger.setLevel(logging.CRITICAL)
# ############################################################################################

consumer_key = getenv('TWITTER_CONSUMER_KEY')
consumer_secret = getenv('TWITTER_CONSUMER_SECRET')
access_token = getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = getenv('TWITTER_ACCESS_TOKEN_SECRET')
bearer_token = getenv('TWITTER_BEARER_TOKEN')


twitter_client = tweepy.asynchronous.AsyncClient(bearer_token)


async def download_twitter_images(session, ctx: Context, *, tweet_ids: str):
    """
    Download image from tweets. \
    Useful for Aluerie bcs twitter is banned in Russia (NotLikeThis).
    <tweet_ids> are tweet ids - it's just numbers in the end of tweet links.
    """
    await ctx.typing()

    if not ctx.interaction:
        await ctx.message.edit(suppress=True)

    tweet_ids = re.split('; |, |,| ', tweet_ids)
    tweet_ids = [t.split('/')[-1].split('?')[0] for t in tweet_ids]

    response = await twitter_client.get_tweets(
        tweet_ids,
        media_fields=["url", "preview_image_url"],
        expansions="attachments.media_keys"
    )
    img_urls = [m.url for m in response.includes['media']]
    files = await url_to_file(session, img_urls, return_list=True)
    split_size = 10
    files_10 = [files[x:x + split_size] for x in range(0, len(files), split_size)]
    for fls in files_10:
        await ctx.reply(files=fls)


followed_array = [
    44680622,   # wykrhm
    176507184,  # dota2
    17388199,   # icefrog
    #1272226371109031937,  # me
]


class MyStreamListener(tweepy.asynchronous.AsyncStream, commands.Cog):
    def __init__(self, bot, consumer_key, consumer_secret, access_token, access_token_secret):
        super().__init__(consumer_key, consumer_secret, access_token, access_token_secret)
        self.bot = bot

    async def on_status(self, tweet):
        if tweet.author.id not in followed_array:
            return
        if tweet.in_reply_to_status_id is not None:
            return
        try:  # retweets between each other
            if tweet.retweeted_status.user.id in followed_array:
                return
        except AttributeError:
            pass
        await self.bot.get_channel(Cid.copydota_tweets).send(
            content=f"https://twitter.com/{tweet.author.screen_name}/status/{tweet.id}")

    async def on_request_error(self, status_code):
        await self.bot.get_channel(Cid.spam_me).send(
            content=f"{umntn(Uid.alu)} I'm stuck with twitter-stream {status_code}")
        self.disconnect()


class Twitter(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.myStream = MyStreamListener(self.bot, consumer_key, consumer_secret, access_token, access_token_secret)
        self.myStream.filter(follow=followed_array)


async def setup(bot):
    await bot.add_cog(Twitter(bot))
