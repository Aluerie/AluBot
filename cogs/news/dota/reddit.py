from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING

import asyncpraw
import discord
from asyncprawcore import AsyncPrawcoreException
from discord.ext import commands, tasks

from utils.var import Clr, Lmt

from cogs.news.dota._base import DotaNewsBase

if TYPE_CHECKING:
    from utils.bot import AluBot


# def silence_event_loop_closed(func):
#     @wraps(func)
#     def wrapper(self, *args, **kwargs):
#         try:
#             return func(self, *args, **kwargs)
#         except RuntimeError as e:
#             if str(e) != 'Event loop is closed':
#                 raise
#
#     return wrapper
#
#
# if platform.system() == 'Windows':
#     # Silence the exception here.
#     _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)

log = logging.getLogger(__name__)


async def process_comments(comment: asyncpraw.reddit.Comment):
    await comment.submission.load()  # DO NOT FORGET TO LOAD
    await comment.subreddit.load()  # DO NOT FORGET TO LOAD
    await comment.author.load()  # DO NOT FORGET TO LOAD

    paginator = commands.Paginator(max_size=Lmt.Embed.description, prefix='', suffix='')
    paginator.add_line(comment.body)

    embeds = [
        discord.Embed(
            title=comment.submission.title[:256], description=page, url=comment.submission.shortlink, colour=Clr.reddit
        )
        for page in paginator.pages
    ]
    embeds[0].set_author(
        name=f'{comment.author.name} commented in r/{comment.subreddit.display_name} post',
        icon_url=comment.author.icon_img,
        url=f'https://www.reddit.com{comment.permalink}',
    )
    return embeds


class Reddit(DotaNewsBase):
    def cog_load(self) -> None:
        self.bot.ini_reddit()
        self.userfeed.start()

    def cog_unload(self) -> None:
        self.userfeed.stop()

    @tasks.loop(minutes=40)
    async def userfeed(self):
        # todo: there is somewhere unclosed client session when running this cog
        log.debug("Starting to stalk u/JeffHill")
        running = 1
        while running:
            try:
                redditor = await self.bot.reddit.redditor("JeffHill")
                async for comment in redditor.stream.comments(skip_existing=True, pause_after=0):
                    if comment is None:
                        continue
                    dtime = datetime.datetime.fromtimestamp(comment.created_utc)
                    # IDK there was some weird bug with sending old messages after 2 months
                    if discord.utils.utcnow() - dtime.replace(tzinfo=datetime.timezone.utc) < datetime.timedelta(
                        days=7
                    ):
                        embeds = await process_comments(comment)
                        for item in embeds:
                            msg = await self.news_channel.send(embed=item)
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


async def setup(bot: AluBot):
    await bot.add_cog(Reddit(bot))
