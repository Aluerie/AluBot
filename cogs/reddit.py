from discord import Embed
from discord.ext import commands, tasks
from utils.var import *
import asyncpraw

import platform
from functools import wraps
from asyncio.proactor_events import _ProactorBasePipeTransport


def silence_event_loop_closed(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != 'Event loop is closed':
                raise

    return wrapper


if platform.system() == 'Windows':
    # Silence the exception here.
    _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)


# import logging
# log = logging.getLogger('root')

from webpreview import web_preview

from os import getenv

reddit = asyncpraw.Reddit(
    client_id=getenv("REDDIT_CLIENT_ID"),
    client_secret=getenv("REDDIT_CLIENT_SECRET"),
    password=getenv("REDDIT_PASSWORD"),
    user_agent=getenv("REDDIT_USER_AGENT"),
    username=getenv("REDDIT_USERNAME")
)

subreddits_array = "DotaPatches"  # "AskReddit+DotaPatches" use '+' to connect them


async def process_submission(submission):
    # log.info("process submission reddit")

    def truncate(msg, num):
        num = num - 2
        return (msg[:num] + '..') if len(msg) > num else msg

    def split(msg, num):
        return [msg[i:i + num] for i in range(0, len(msg), num)]

    sub = submission.subreddit.display_name
    is_cross = 0
    footnote_text = ''
    old_url = ''
    # print(submission.title)
    try:
        cross = submission.crosspost_parent
        cross_url = f'https://redd.it/{cross.split("_")[1]}'
        parent = await reddit.submission(url=cross_url)
        parent_subreddit = parent.subreddit.display_name
        # print(parent_subreddit,sub)
        if sub != parent_subreddit:
            is_cross = 1
            old_url = submission.shortlink
            submission = parent
            footnote_text = f'Crosspost in /r/{sub} from /r/{parent_subreddit}'
    except:
        pass

    url = submission.url
    selftext = split(submission.selftext, 2048)
    embed = Embed(colour=0xFF4500)
    if submission.is_self is True:
        posttype = 'self'
        if len(selftext) > 0:
            embed.description = selftext[0]
    elif url.endswith("jpg") or url.endswith("jpeg") or url.endswith("png"):
        embed.set_image(url=url)
        posttype = 'image'
    else:
        posttype = 'link'
        link_title, link_description, link_image = web_preview(url, parser='lxml')
        embed.description = f'{url}'  # , link_title, link_description)
        if link_image is not None:
            embed.set_image(url=link_image)
    embed.set_author(
        name=f'{posttype}-post on /r/{sub} by /u/{submission.author}',
        url=submission.shortlink,
        icon_url='https://www.redditinc.com/assets/images/site/reddit-logo.png'
    )
    embed.title = truncate(submission.title, 256)
    embed.url = submission.shortlink
    if is_cross:
        embed.add_field(name=footnote_text, value=f'[Crosspost link]({old_url})')

    embeds = [embed]
    if len(selftext) > 1:
        for text in selftext[1:]:
            embed = Embed(colour=0xFF4500)
            embed.description = text
            embeds.append(embed)
    return embeds


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redditfeed.start()

    @tasks.loop(minutes=10)
    async def redditfeed(self):
        # log.info("redditfeed every 10 minutes")
        try:
            subreddit = await reddit.subreddit(subreddits_array)
        except Exception as e:
            print("redditfeed error line 108 Sadge", e)
            return

        reddit_channel = self.bot.get_channel(Cid.dota_news)  # Cid.spam_me

        async for submission in subreddit.stream.submissions(skip_existing=True):
            embeds = await process_submission(submission)
            for item in embeds:
                msg = await reddit_channel.send(embed=item)
                await msg.publish()

    @redditfeed.before_loop
    async def before(self):
        # log.info("redditfeed before loop")
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Reddit(bot))
