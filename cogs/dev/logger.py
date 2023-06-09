from __future__ import annotations

import asyncio
import datetime
import logging
import textwrap
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

from ._base import DevBaseCog

if TYPE_CHECKING:
    from utils import AluBot

log = logging.getLogger(__name__)


class LoggingHandler(logging.Handler):
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
        # TODO: if we find a better purpose then move this to the AluBot class
        url = self.bot.config.SPAM_LOGS_WEBHOOK_URL
        hook = discord.Webhook.from_url(url=url, session=self.bot.session)
        return hook
    
    def add_record(self, record: logging.LogRecord) -> None:
        self._logging_queue.put_nowait(record)

    async def send_log_record(self, record: logging.LogRecord) -> None:
        # TODO: customize this
        attributes = {'INFO': '\N{INFORMATION SOURCE}\ufe0f', 'WARNING': '\N{WARNING SIGN}\ufe0f'}

        emoji = attributes.get(record.levelname, '\N{CROSS MARK}')
        dt = datetime.datetime.utcfromtimestamp(record.created)
        msg = textwrap.shorten(f'{emoji} {self.bot.formats.format_dt(dt)} {record.message}', width=1990)
        if record.name == 'discord.gateway':
            username = 'Gateway'
            avatar_url = 'https://i.imgur.com/4PnCKB3.png'
        else:
            username = f'{record.name} Logger'.replace('discord', 'dcord')
            avatar_url = discord.utils.MISSING
        await self.logger_webhook.send(msg, username=username, avatar_url=avatar_url)

    @tasks.loop(seconds=0.0)
    async def logging_worker(self):
        record = await self._logging_queue.get()
        await self.send_log_record(record)

async def setup(bot: AluBot):
    if bot.test:
        # Ehh, let's not spam these with testing bots
        return
    cog = LoggerViaWebhook(bot)
    await bot.add_cog(cog)
    bot.logging_handler = handler = LoggingHandler(cog)
    logging.getLogger().addHandler(handler)


async def teardown(bot: AluBot):
    if bot.test:
        return
    logging.getLogger().removeHandler(bot.logging_handler)
    del bot.logging_handler