from __future__ import annotations

import asyncio
import datetime
import logging
import textwrap
from typing import TYPE_CHECKING, Any, override

import discord
from discord.ext import tasks

from config import SPAM_LOGS_WEBHOOK
from utils import AluCog, const, formats

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bot import AluBot

log = logging.getLogger(__name__)


class LoggingHandler(logging.Handler):
    """Extra logging handler to output info/warning/errors to a discord webhook.

    * Just remember that `log.info` and above calls go spammed in a discord webhook so plan them accordingly.
    * `log.debug` is not so use primarily them for debug logs (they only get saved in .log file)
    """

    def __init__(self, cog: LoggerViaWebhook) -> None:
        self.cog: LoggerViaWebhook = cog
        super().__init__(logging.INFO)

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out some somewhat pointless messages so we don't spam the channel as much."""

        messages_to_ignore = (
            "Clock drift detected for task",  # idk, I won't do anything about any of those messages.
            "Shard ID None has successfully RESUMED",
            "Shard ID None has connected to Gateway",
        )
        if any(msg in record.message for msg in messages_to_ignore):
            return False

        return True  # record.name in ('discord.gateway')

    @override
    def emit(self, record: logging.LogRecord) -> None:
        self.cog.add_record(record)


class LoggerViaWebhook(AluCog):
    """Logger Via Webhook - providing handler to send logs in a discord channel

    This is basically an extra logging handler that uses discord webhook to print the messages.
    Kinda pointless, but at the same time, very handy to have an easy to check, easy to view channel with messages
    which is being spammed with errors if something is catastrophically wrong that it doesn't go to error handlers.
    """

    # TODO: ADD MORE STUFF
    AVATAR_MAPPING: Mapping[str, str] = {
        "discord.gateway": "https://i.imgur.com/4PnCKB3.png",
        "discord.ext.tasks": "https://em-content.zobj.net/source/microsoft/378/alarm-clock_23f0.png",
        "bot.bot": "https://i.imgur.com/6XZ8Roa.png",  # lady Noir
        "send_dota_fpc": "https://i.imgur.com/67ipDvY.png",  # dota 2
        "edit_dota_fpc": "https://i.imgur.com/nkcvMa2.png",  # dota 2
        "ext.dev.sync": "https://em-content.zobj.net/source/microsoft/378/counterclockwise-arrows-button_1f504.png",
        "utils.dota.valvepythondota2": "https://i.imgur.com/D96bMgG.png",
        "utils.dota.dota2client": "https://i.imgur.com/D96bMgG.png",
        "exc_manager": "https://em-content.zobj.net/source/microsoft/378/sos-button_1f198.png",
        "twitchio.ext.eventsub.ws": const.Logo.Twitch,
        "twitchio.websocket": const.Logo.Twitch,
        # "https://em-content.zobj.net/source/microsoft/378/swan_1f9a2.png",
        "ext.fpc.lol.notifications": const.Logo.Lol,
        "githubkit": "https://seeklogo.com/images/G/github-colored-logo-FDDF6EB1F0-seeklogo.com.png",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._logging_queue = asyncio.Queue()

    @override
    async def cog_load(self) -> None:
        self.logging_worker.start()

    @override
    def cog_unload(self) -> None:
        self.logging_worker.stop()

    @discord.utils.cached_property
    def logger_webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(url=SPAM_LOGS_WEBHOOK, session=self.bot.session)

    def add_record(self, record: logging.LogRecord) -> None:
        self._logging_queue.put_nowait(record)

    async def send_log_record(self, record: logging.LogRecord) -> None:
        attributes = {
            "INFO": "\N{INFORMATION SOURCE}\ufe0f",
            "WARNING": "\N{WARNING SIGN}\ufe0f",
            "ERROR": "\N{CROSS MARK}",
        }

        emoji = attributes.get(record.levelname, "\N{WHITE QUESTION MARK ORNAMENT}")
        # the time is there so the MM:SS is more clear. Discord stacks messages from the same webhook user
        # so if logger sends at 23:01 and 23:02 it will be hard to understand the time difference
        dt = datetime.datetime.fromtimestamp(record.created, datetime.UTC)
        msg = textwrap.shorten(f"{emoji} {formats.format_dt(dt, style="T")} {record.message}", width=1995)
        avatar_url = self.AVATAR_MAPPING.get(record.name, discord.utils.MISSING)

        # Discord doesn't allow Webhooks names to contain "discord";
        # so if the record.name comes from discord.py library - it gonna block it
        # thus we replace letters: "c" is cyrillic, "o" is greek.
        username = record.name.replace("discord", "disсοrd")  # cSpell: ignore disсοrd  # noqa: RUF003
        await self.logger_webhook.send(msg, username=username, avatar_url=avatar_url)

    @tasks.loop(seconds=0.0)
    async def logging_worker(self) -> None:
        record = await self._logging_queue.get()
        await self.send_log_record(record)


async def setup(bot: AluBot) -> None:
    """Setup

    Reason this is in core extensions because some `cog_load` have pretty important log messages
    that we want to log into the webhook. So we want to load this as early as possible.

    If we ever need even earlier load then we will have to
    manually order extensions in __init__ or at least bump this one
    """
    if bot.test:
        # no need since I'm directly watching.
        return

    cog = LoggerViaWebhook(bot)
    await bot.add_cog(cog)
    bot.logging_handler = handler = LoggingHandler(cog)
    logging.getLogger().addHandler(handler)


async def teardown(bot: AluBot) -> None:
    if bot.test:
        return

    log.warning("Tearing down logger via webhook.")
    logging.getLogger().removeHandler(bot.logging_handler)
    del bot.logging_handler
