from __future__ import annotations

import asyncio
import platform
from asyncio.proactor_events import _ProactorBasePipeTransport
from datetime import datetime, timedelta, timezone
from functools import wraps
import logging
from typing import TYPE_CHECKING

import asyncpraw
from asyncprawcore import AsyncPrawcoreException
from discord import Embed
from discord.ext import commands, tasks

from .utils.var import Lmt, Cid, Clr

if TYPE_CHECKING:
    from .utils.bot import AluBot


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

log = logging.getLogger(__name__)


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
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.userfeed.start()

    def cog_load(self) -> None:
        self.bot.ini_reddit()

    def cog_unload(self) -> None:
        self.userfeed.cancel()

    @tasks.loop(minutes=40)
    async def userfeed(self):
        log.debug("Starting to stalk u/JeffHill")
        running = 1
        while running:
            try:
                redditor = await self.bot.reddit.redditor("JeffHill")
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
        await self.bot.send_traceback(error, where='Error in reddit userfeed')
        await asyncio.sleep(60)
        self.userfeed.restart()


async def setup(bot):
    await bot.add_cog(Reddit(bot))
