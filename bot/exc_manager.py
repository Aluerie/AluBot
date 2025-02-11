"""ex_manager.py - yes, it is for managing my exes."""

from __future__ import annotations

import asyncio
import datetime
import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    import discord

    from .bot import AluBot


log = logging.getLogger("exc_manager")


class ExceptionManager:
    """Exception Manager that.

    * should be used to send all unhandled errors to developers via webhooks.
    * controls rate-limit of the said webhook
    * contains history of errors that was not fixed yet
    * allows users to track the said errors and get notification when it's fixed

    Attributes
    ----------
    bot : AluBot
        The bot instance.
    cooldown : datetime.timedelta
        The cooldown between sending errors. This defaults to 5 seconds.
    errors_cache : dict[str, list[ErrorInfoPacket]]
        A mapping of tracebacks to their error information.
    error_webhook : discord.Webhook
        The error webhook used to send errors.

    """

    # Inspired by:
    # licensed MPL v2 from DuckBot-Discord/DuckBot
    # https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/errorhandler.py

    __slots__: tuple[str, ...] = (
        "_lock",
        "_most_recent",
        "bot",
        "cooldown",
        "errors_cache",
    )

    def __init__(
        self,
        bot: AluBot,
        *,
        cooldown: datetime.timedelta = datetime.timedelta(seconds=5),
    ) -> None:
        self.bot: AluBot = bot
        self.cooldown: datetime.timedelta = cooldown

        self._lock: asyncio.Lock = asyncio.Lock()
        self._most_recent: datetime.datetime | None = None

    def _yield_code_chunks(self, iterable: str, *, chunks_size: int = 2000) -> Generator[str, None, None]:
        codeblocks: str = "```py\n{}```"
        max_chars_in_code = chunks_size - (len(codeblocks) - 2)  # chunks_size minus code blocker size

        for i in range(0, len(iterable), max_chars_in_code):
            yield codeblocks.format(iterable[i : i + max_chars_in_code])

    async def register_error(
        self,
        error: BaseException,
        embed: discord.Embed,
        channel_id: int | None = None,
        *,
        log_message: str | None = None,
    ) -> None:
        """Register, analyse error and put it into queue to send to developers.

        Parameters
        ----------
        error: Exception
            Exception that the developers of AluBot are going to be notified about
        embed: discord.Embed
            Embed to send after traceback messages.
            This should showcase some information that can't be gotten from the error, i.e.
            discord author information, guild where the error happened, some snowflakes, etc.
        log_message: str = ""
            Message to send to `log.error`. If none provided, it will use string from `embed.footer.text`.
        channel_id: int | None = None
            Channel where the error occurred. If this is one of developer's test channels then the `embed` from
            will be omitted. `None` option forces sending that embed.
            Example: a developer uses a slash command in a test channel expecting an error.
            Then embed with slash command arguments is useless because that information is right there anyway.

        """
        log_message = log_message if log_message is not None else embed.footer.text
        log.error("%s: `%s`.", error.__class__.__name__, log_message, exc_info=error)

        # apparently there is https://github.com/vi3k6i5/flashtext for "the fastest replacement"
        # not sure if I want to add an extra dependency
        traceback_string = "".join(traceback.format_exception(error)).replace(str(Path.cwd()), "AluBot")
        traceback_string = traceback_string.replace("``", "`\u200b`")

        async with self._lock:
            if self._most_recent and (delta := datetime.datetime.now(datetime.UTC) - self._most_recent) < self.cooldown:
                # We have to wait
                total_seconds = delta.total_seconds()
                log.debug("Waiting %s seconds to send the error.", total_seconds)
                await asyncio.sleep(total_seconds)

            self._most_recent = datetime.datetime.now(datetime.UTC)
            await self.send_error(traceback_string, embed, channel_id=channel_id)

    async def send_error(self, traceback: str, embed: discord.Embed, *, channel_id: int | None = None) -> None:
        """Send an error to the error webhook.

        It is not recommended to call this yourself, call `register_error` instead.

        Parameters
        ----------
        traceback: str
            The traceback of the error.
        embed: discord.Embed
            The additional information about the error. This comes from registering the error.
        channel_id: int | None = None
            Channel ID coming from `register_error`.
        """
        code_chunks = list(self._yield_code_chunks(traceback))

        # hmm, this is honestly a bit too many sends for 5 seconds of rate limit :thinking:

        # if channel_id != self.bot.hideout.spam_channel_id:
        try:
            await self.bot.error_webhook.send(self.bot.error_ping)

            for chunk in code_chunks:
                await self.bot.error_webhook.send(chunk)

            if channel_id != self.bot.hideout.spam_channel_id:
                await self.bot.error_webhook.send(embed=embed)
        except discord.HTTPException as error:
            warning = f"{self.bot.error_ping} {error.__class__.__name__} {error}"
            await self.bot.spam_webhook.send(warning)
