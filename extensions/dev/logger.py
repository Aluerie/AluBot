from __future__ import annotations

import asyncio
import datetime
import logging
import textwrap
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

from config import SPAM_LOGS_WEBHOOK
from utils import formats

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot

log = logging.getLogger(__name__)


class LoggingHandler(logging.Handler):
    """Extra logging handler to output info/warning/errors to a discord webhook.

    * Just remember that `log.info` and above calls go spammed in a discord webhook so plan them accordingly.
    * `log.debug` do not so use primarily them for debug logs
    """

    def __init__(self, cog: LoggerViaWebhook):
        self.cog: LoggerViaWebhook = cog
        super().__init__(logging.INFO)

    def filter(self, record: logging.LogRecord) -> bool:
        return True  # record.name in ('discord.gateway')

    def emit(self, record: logging.LogRecord) -> None:
        self.cog.add_record(record)


class LoggerViaWebhook(DevBaseCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logging_queue = asyncio.Queue()

    async def cog_load(self) -> None:
        self.logging_worker.start()

    def cog_unload(self) -> None:
        self.logging_worker.cancel()

    @discord.utils.cached_property
    def logger_webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(url=SPAM_LOGS_WEBHOOK, session=self.bot.session)

    def add_record(self, record: logging.LogRecord) -> None:
        self._logging_queue.put_nowait(record)

    # TODO: ADD MORE STUFF
    avatar_mapping = {
        "discord.gateway": "https://i.imgur.com/4PnCKB3.png",
        "discord.ext.tasks": "https://em-content.zobj.net/source/microsoft/378/alarm-clock_23f0.png",
        "bot.bot": "https://em-content.zobj.net/source/microsoft/378/swan_1f9a2.png",
    }

    async def send_log_record(self, record: logging.LogRecord) -> None:
        attributes = {
            "INFO": "\N{INFORMATION SOURCE}\ufe0f",
            "WARNING": "\N{WARNING SIGN}\ufe0f",
            "ERROR": "\N{CROSS MARK}",
        }

        emoji = attributes.get(record.levelname, "\N{WHITE QUESTION MARK ORNAMENT}")
        dt = datetime.datetime.utcfromtimestamp(record.created)
        msg = textwrap.shorten(f"{emoji} {formats.format_dt(dt)} {record.message}", width=1990)

        avatar_url = self.avatar_mapping.get(record.name, discord.utils.MISSING)
        # Discord doesn't allow Webhooks names to contain "discord";
        # so if the record.name comes from discord library - it gonna block it
        # thus we replace letters. c is cyrillic, o is greek.
        username = record.name.replace("discord", "disсοrd")
        await self.logger_webhook.send(msg, username=username, avatar_url=avatar_url)

    @tasks.loop(seconds=0.0)
    async def logging_worker(self):
        record = await self._logging_queue.get()
        await self.send_log_record(record)


async def setup(bot: AluBot):
    cog = LoggerViaWebhook(bot)
    await bot.add_cog(cog)
    bot.logging_handler = handler = LoggingHandler(cog)
    logging.getLogger().addHandler(handler)


async def teardown(bot: AluBot):
    logging.getLogger().removeHandler(bot.logging_handler)
    del bot.logging_handler
