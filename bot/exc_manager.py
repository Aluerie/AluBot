"""ex_manager.py - yes, it is for managing my exes."""

from __future__ import annotations

import asyncio
import datetime
import logging
import traceback
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, override

import discord

import config
from utils import const, errors

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType

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
        "bot",
        "cooldown",
        "errors_cache",
        "_lock",
        "_most_recent",
        "error_webhook",
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

        webhook_url = config.TEST_ERROR_HANDLER_WEBHOOK if self.bot.test else config.MAIN_ERROR_HANDLER_WEBHOOK
        self.error_webhook: discord.Webhook = discord.Webhook.from_url(
            url=webhook_url,
            session=bot.session,
            client=bot,
            bot_token=bot.http.token,
        )

    def _yield_code_chunks(self, iterable: str, *, chunks_size: int = 2000) -> Generator[str, None, None]:
        codeblocks: str = "```py\n{}```"
        max_chars_in_code = chunks_size - (len(codeblocks) - 2)  # chunks_size minus code blocker size

        for i in range(0, len(iterable), max_chars_in_code):
            yield codeblocks.format(iterable[i : i + max_chars_in_code])

    async def register_error(
        self,
        error: BaseException,
        embed: discord.Embed,
        *,
        mention: bool = True,
    ) -> None:
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
        mention : bool
            Whether to mention Irene when releasing the error to the webhook
        """
        log.error("%s: `%s`.", error.__class__.__name__, embed.footer.text, exc_info=error)

        # apparently there is https://github.com/vi3k6i5/flashtext for "the fastest replacement"
        # not sure if I want to add extra dependance
        traceback_string = "".join(traceback.format_exception(error)).replace(str(Path.cwd()), "AluBot")
        # .replace("``": "`\u200b`")

        async with self._lock:
            if self._most_recent and (delta := datetime.datetime.now(datetime.UTC) - self._most_recent) < self.cooldown:
                # We have to wait
                total_seconds = delta.total_seconds()
                log.debug("Waiting %s seconds to send the error.", total_seconds)
                await asyncio.sleep(total_seconds)

            self._most_recent = datetime.datetime.now(datetime.UTC)
            await self.send_error(traceback_string, embed, mention)

    async def send_error(self, traceback: str, embed: discord.Embed, mention: bool) -> None:
        """Send an error to the webhook.
        It is not recommended to call this yourself, call `register_error` instead.

        Parameters
        ----------
        traceback : str
            The traceback of the error.
        embed : discord.Embed
            The additional information about the error. This comes from registering the error.
        mention : bool
            Whether to send said embed and ping Irene at all.
        """
        code_chunks = list(self._yield_code_chunks(traceback))

        # hmm, this is honestly a bit too many sends for 5 seconds of rate limit :thinking:
        if mention:
            await self.error_webhook.send(const.Role.error_ping.mention)

        for chunk in code_chunks:
            await self.error_webhook.send(chunk)

        if mention:
            await self.error_webhook.send(embed=embed)


class HandleHTTPException(AbstractAsyncContextManager[Any]):
    """Context manger to handle HTTP Exceptions.

    This is useful for handling errors that are not critical, but
    still need to be reported to the user.

    Parameters
    ----------
    destination: discord.abc.Messageable
        The destination channel to send the error to.
    title: str | None
        The title of the embed. Defaults to ``'An unexpected error occurred!'``.

    Attributes
    ----------
    destination: discord.abc.Messageable
        The destination channel to send the error to.
    message: str | None
        The string to put the embed title in.

    Raises
    ------
    SilentCommandError
        Error raised if an HTTPException is encountered. This
        error is specifically ignored by the command error handler.

    """

    __slots__ = ("destination", "title")

    def __init__(self, destination: discord.abc.Messageable, *, title: str | None = None) -> None:
        self.destination = destination
        self.title = title

    @override
    async def __aenter__(self) -> Self:
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool:
        if exc_val is not None and isinstance(exc_val, discord.HTTPException) and exc_type:
            embed = discord.Embed(
                title=self.title or "An unexpected error occurred!",
                description=f"{exc_type.__name__}: {exc_val.text}",
                colour=discord.Colour.red(),
            )

            await self.destination.send(embed=embed)
            raise errors.SilentError

        return False
