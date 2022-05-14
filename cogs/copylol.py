from discord.ext import commands
from utils.var import Cid, Uid, umntn
from utils.format import block_function
from utils.inettools import replace_tco_links, move_link_to_title, get_links_from_str

import re
import tweepy
import traceback
import asyncio

from os import getenv
GIT_KEY = getenv("GIT_KEY")


consumer_key = getenv('TWITTER_CONSUMER_KEY')
consumer_secret = getenv('TWITTER_CONSUMER_SECRET')
access_token = getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = getenv('TWITTER_ACCESS_TOKEN_SECRET')
bearer_token = getenv('TWITTER_BEARER_TOKEN')
client = tweepy.Client(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret)


class CopypasteLeague(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    blocked_words = [
        'Free Champion Rotation',
        'PlayRuneterra',
        'RiotForge',
        'TFT',
        'Teamfight Tactics',
        'Mortdog',
        'Champion & Skin Sale',
        'Champion &amp; Skin Sale',
        'prime gaming',
        'wildrift',
        'Wild Rift',
        'entwuhoo'  # tft dev account
    ]

    whitelist_words = [
        ' Notes',
    ]

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.channel.id == Cid.copylol_ff20:
                if block_function(message.content, self.blocked_words, self.whitelist_words):
                    return

                embeds = None  # TODO: if they start using actual bots then this wont work
                content = message.content
                if "https://twitter.com" in message.content:
                    await asyncio.sleep(2)
                    answer = await message.channel.fetch_message(int(message.id))
                    for match in re.findall(r'status/(\d+)', answer.content):
                        status = client.get_tweet(int(match))
                        if block_function(status.data.text, self.blocked_words, self.whitelist_words):
                            return
                    embeds = [await replace_tco_links(item) for item in message.embeds]
                    links = get_links_from_str(answer.content)
                    embeds = [move_link_to_title(link, embed) for link, embed in zip(links, embeds)]
                    content = ''

                files = [await item.to_file() for item in message.attachments]
                msg = await self.bot.get_channel(Cid.lol_news).send(content=content, embeds=embeds, files=files)
                await msg.publish()
        except Exception as e:
            error_message = traceback.format_exc()
            await self.bot.get_channel(Cid.spam_me).send(
                f'{umntn(Uid.irene)} Something went wrong with #league-news copypaste\n'
                f'```python\n{error_message}```')


def setup(bot):
    bot.add_cog(CopypasteLeague(bot))
