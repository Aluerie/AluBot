from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from asyncprawcore import AsyncPrawcoreException
from discord import Embed
from discord.ext import commands, tasks

from config import (
    REDDIT_CLIENT_ID, REDDIT_PASSWORD, REDDIT_USER_AGENT, REDDIT_USERNAME, REDDIT_CLIENT_SECRET
)
from utils.distools import send_traceback
from utils.var import *
import asyncpraw

import platform
from functools import wraps
from asyncio.proactor_events import _ProactorBasePipeTransport

if TYPE_CHECKING:
    from utils.bot import AluBot


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


import logging
log = logging.getLogger('root')

from webpreview import web_preview


reddit = asyncpraw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT,
    username=REDDIT_USERNAME
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
            embed = Embed(colour=0xFF4500, description=text)
            embeds.append(embed)
    return embeds


async def process_comments(comment: asyncpraw.reddit.Comment):
    await comment.submission.load()  # DO NOT FORGET TO LOAD
    await comment.subreddit.load()  # DO NOT FORGET TO LOAD
    await comment.author.load()  # DO NOT FORGET TO LOAD

    paginator = commands.Paginator(
        prefix='',
        suffix='',
        max_size=Lmt.Embed.description,
    )
    paginator.add_line(comment.body)

    embeds = [
        Embed(
            colour=0xFF4500,
            title=comment.submission.title[:256],
            url=comment.submission.shortlink,
            description=page
        )
        for page in paginator.pages
    ]
    embeds[0].set_author(
        name=f'{comment.author.name} commented in r/{comment.subreddit.display_name} post',
        icon_url=comment.author.icon_img,
        url=f'https://www.reddit.com{comment.permalink}'
    )
    return embeds


class Reddit(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot = bot
        self.redditfeed.start()
        self.userfeed.start()

    def cog_unload(self) -> None:
        self.redditfeed.cancel()
        self.userfeed.cancel()

    @tasks.loop(minutes=40)
    async def redditfeed(self):
        log.info("Starting to stalk r/DotaPatches")
        running = 1
        while running:
            try:
                subreddit = await reddit.subreddit(subreddits_array)
                async for submission in subreddit.stream.submissions(skip_existing=True, pause_after=0):
                    if submission is None:
                        continue
                    embeds = await process_submission(submission)
                    for item in embeds:
                        msg = await self.bot.get_channel(Cid.dota_news).send(embed=item)
                        await msg.publish()
            except AsyncPrawcoreException:
                await asyncio.sleep(60 * running)
                running += 1

    @redditfeed.before_loop
    async def before(self):
        # log.info("redditfeed before loop")
        await self.bot.wait_until_ready()

    @redditfeed.error
    async def redditfeed_error(self, error):
        # TODO: write if isinstance(RunTimeError): be silent else do send_traceback or something,
        #  probably declare your own error type
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in subreddit feed'))
        await asyncio.sleep(60)
        self.redditfeed.restart()

    @tasks.loop(minutes=40)
    async def userfeed(self):
        log.info("Starting to stalk u/JeffHill")
        running = 1
        while running:
            try:
                redditor = await reddit.redditor("JeffHill")
                async for comment in redditor.stream.comments(skip_existing=True, pause_after=0):
                    if comment is None:
                        continue
                    dtime = datetime.fromtimestamp(comment.created_utc)
                    # IDK there was some weird bug with sending old messages after 2 months
                    if datetime.now(timezone.utc) - dtime.replace(tzinfo=timezone.utc) < timedelta(days=7):
                        embeds = await process_comments(comment)
                        for item in embeds:
                            msg = await self.bot.get_channel(Cid.spam_me).send(embed=item)
                            await msg.publish()
            except AsyncPrawcoreException:
                await asyncio.sleep(60 * running)
                running += 1

    @userfeed.before_loop
    async def before(self):
        # log.info("redditfeed before loop")
        await self.bot.wait_until_ready()

    @userfeed.error
    async def userfeed_error(self, error):
        # TODO: write if isinstance(RunTimeError): be silent else do send_traceback or something,
        #  probably declare your own error type
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in reddit userfeed'))
        await asyncio.sleep(60)
        self.userfeed.restart()


async def setup(bot):
    await bot.add_cog(Reddit(bot))
