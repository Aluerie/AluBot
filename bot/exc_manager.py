"""ex_manager.py - yes, it is for managing my exes."""

from __future__ import annotations

import asyncio
import datetime
import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from utils import const

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

    async def register_error(self, error: BaseException, embed: discord.Embed) -> None:
        """Register, analyse error and put it into queue to send to developers.

        Parameters
        ----------
        error : Exception
            Exception that the developers of AluBot are going to be notified about
        embed : discord.Embed
            Embed to send after traceback messages.
            This should showcase some information that can't be gotten from the error, i.e.
            discord author information, guild where the error happened, some snowflakes, etc.

            Look the template of the formatting for this in something like `ctx_cmd_errors.py`.

            Important!!! Embed's footer text will be duplicated to `log.error` so choose the wording carefully.
        """
        log.error("%s: `%s`.", error.__class__.__name__, embed.footer.text, exc_info=error)

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
            await self.send_error(traceback_string, embed)

    async def send_error(self, traceback: str, embed: discord.Embed) -> None:
        """Send an error to the error webhook.

        It is not recommended to call this yourself, call `register_error` instead.

        Parameters
        ----------
        traceback : str
            The traceback of the error.
        embed : discord.Embed
            The additional information about the error. This comes from registering the error.

        """
        code_chunks = list(self._yield_code_chunks(traceback))

        # hmm, this is honestly a bit too many sends for 5 seconds of rate limit :thinking:
        if not self.bot.test:
            # i don't need any extra pings when I'm testing since I'm right there.
            await self.bot.error_webhook.send(const.Role.error.mention)

        for chunk in code_chunks:
            await self.bot.error_webhook.send(chunk)
        await self.bot.error_webhook.send(embed=embed)
