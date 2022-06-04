import tweepy.asynchronous
from discord.ext import commands
from utils.var import Cid, Uid, umntn
from os import getenv

# #################### WHILE TWITTER IS BANNED IN RUSSIA #####################################
# TODO: remove this when twitter is unbanned
import logging
logger = logging.getLogger('tweepy')
logger.setLevel(logging.CRITICAL)
# ############################################################################################

consumer_key = getenv('TWITTER_CONSUMER_KEY')
consumer_secret = getenv('TWITTER_CONSUMER_SECRET')
access_token = getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = getenv('TWITTER_ACCESS_TOKEN_SECRET')
bearer_token = getenv('TWITTER_BEARER_TOKEN')

followed_array = [
    44680622,   # wykrhm
    176507184,  # dota2
    17388199,   # icefrog
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
        self.bot = bot
        self.myStream = MyStreamListener(self.bot, consumer_key, consumer_secret, access_token, access_token_secret)
        self.myStream.filter(follow=followed_array)


async def setup(bot):
    await bot.add_cog(Twitter(bot))
