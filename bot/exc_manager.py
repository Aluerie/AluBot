"""
ex_manager.py - yes, it is for managing my exes.
"""

from __future__ import annotations

import asyncio
import datetime
import inspect
import logging
import os
import traceback
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, NamedTuple

import discord

import config
from utils import AluContext, const, errors

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType

    from .bot import AluBot


log = logging.getLogger("exc_manager")


class ErrorInfoPacket(NamedTuple):
    """
    Parameters
    ----------
    embed: discord.Embed
        embed to send in error notification to the devs
    dt: datetime.datetime
        datetime.datetime to compare for rate-limit purposes
    mention: bool
        whether mention the devs.
        Useful if I'm sitting in debug-spam channel so I don't get unnecessary pings.
    """

    embed: discord.Embed
    dt: datetime.datetime
    mention: bool


class ExceptionManager:
    """Exception Manager that

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

        self.errors_cache: dict[str, list[ErrorInfoPacket]] = {}

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

    async def send_error(self, traceback: str, packet: ErrorInfoPacket) -> None:
        """Send an error to the webhook and log it to the console.
        It is not recommended to call this yourself, call `register_error` instead.

        Parameters
        ----------
        traceback: str
            The traceback of the error.
        packet: ErrorInfoPacket
            The additional information about the error.
        """

        code_chunks = list(self._yield_code_chunks(traceback))

        # hmm, this is honestly a bit too many sends for 5 seconds of rate limit :thinking:
        if packet.mention:
            await self.error_webhook.send(const.Role.error_ping.mention)

        for chunk in code_chunks:
            await self.error_webhook.send(chunk)

        if packet.mention:
            await self.error_webhook.send(embed=packet.embed)

    async def get_info_packet(
        self,
        source: discord.Interaction[AluBot] | AluContext | discord.Embed | str | None,
        where: str,
        extra: str | None,
    ) -> ErrorInfoPacket:
        """Get info packet"""

        if isinstance(source, str):
            dt = discord.utils.utcnow()
            embed = discord.Embed(colour=0xDA9F93, description=source, timestamp=dt).set_footer(text=where)
            return ErrorInfoPacket(embed=embed, dt=dt, mention=True)

        if isinstance(source, discord.Embed):
            if not source.timestamp:
                source.timestamp = dt = discord.utils.utcnow()
            else:
                dt = source.timestamp
            return ErrorInfoPacket(embed=source, dt=dt, mention=True)

        elif isinstance(source, AluContext):
            ctx = source  # I just can't type `source.command.qualified_name` lol

            embed = discord.Embed(
                colour=0x890620,
                title=f"`{ctx.clean_prefix}{ctx.command}`",
                url=ctx.message.jump_url,
                description=ctx.message.content,
            )

            # metadata
            author_text = f"@{ctx.author} triggered error in #{ctx.channel}"
            embed.set_author(name=author_text, icon_url=ctx.author.display_avatar)
            if ctx.guild:
                embed.set_footer(text=f"{ctx.guild.name}\n{where}", icon_url=ctx.guild.icon)
                guild_id = ctx.guild.id
            else:
                guild_id = "DM Channel"
                embed.set_footer(text=f"DM Channel\n{where}", icon_url=ctx.author.display_avatar)

            # arguments
            args_str = ["```py"]
            for name, value in ctx.kwargs.items():
                args_str.append(f"[{name}]: {value!r}")
            else:
                args_str.append("No arguments")
            args_str.append("```")
            embed.add_field(name="Command Args", value="\n".join(args_str), inline=False)

            # ids
            embed.add_field(
                name="Snowflake Ids",
                value=(
                    "```py\n"
                    f"author  = {ctx.author.id}\n"
                    f"channel = {ctx.channel.id}\n"
                    f"guild   = {guild_id}\n```"
                ),
            )

            embed.timestamp = dt = ctx.message.created_at
            mention = ctx.channel.id != ctx.bot.hideout.spam_channel_id
            return ErrorInfoPacket(embed=embed, dt=dt, mention=mention)

        elif isinstance(source, discord.Interaction):
            interaction = source

            app_cmd = interaction.command
            if app_cmd:
                embed = discord.Embed(colour=0x2C0703)
                embed.title = f"`/{app_cmd.qualified_name}`"

                # arguments
                args_str = ["```py"]
                for name, value in interaction.namespace.__dict__.items():
                    args_str.append(f"[{name}]: {value!r}")
                else:
                    args_str.append("No arguments")
                args_str.append("```")
                embed.add_field(name="Command Args", value="\n".join(args_str), inline=False)
            else:
                embed = discord.Embed(colour=0x2A0553)
                embed.title = "Non cmd (View?) interaction"

            # metadata
            author_text = f"@{interaction.user} triggered error in #{interaction.channel}"
            embed.set_author(name=author_text, icon_url=interaction.user.display_avatar)
            if interaction.guild:
                embed.set_footer(text=f"{interaction.guild.name}\n{where}", icon_url=interaction.guild.icon)
                guild_id = interaction.guild.id
            else:
                guild_id = "DM Channel"
                embed.set_footer(text=f"DM Channel\n{where}", icon_url=interaction.user.display_avatar)

            if extra:
                embed.add_field(name="Extra Data", value=extra)

            # ids
            embed.add_field(
                name="Snowflake Ids",
                value=inspect.cleandoc(
                    f"""```py
                    author  = {interaction.user.id}
                    channel = {interaction.channel_id}
                    guild   = {interaction.guild_id}```"""
                ),
                inline=False,
            )
            embed.timestamp = dt = interaction.created_at
            mention = interaction.channel_id != interaction.client.hideout.spam_channel_id
            return ErrorInfoPacket(embed=embed, dt=discord.utils.utcnow(), mention=mention)
        else:
            # shouldn't ever trigger
            # probably source is `None`, but let's leave it as "else" for some silly mistake too.
            embed = discord.Embed(colour=const.Colour.maroon)
            embed.description = "Something went wrong somewhere. Please make it so next time it says where here."
            embed.timestamp = dt = discord.utils.utcnow()
            embed.set_footer(text=where)
            return ErrorInfoPacket(embed=embed, dt=dt, mention=True)

    async def register_error(
        self,
        error: BaseException,
        source: discord.Interaction[AluBot] | AluContext | discord.Embed | str | None,
        *,
        where: str,
        extra: str | None = None,
    ):
        """Register, analyse error and put it into queue to send to developers

        Parameters
        -----------
        error: Exception
            Exception that the developers of AluBot are going to be notified about
        source: discord.Interaction[AluBot] | AluContext | discord.Embed | str | None,
            "source" object of the error. It's basically conditional context
            of where the error happened. Can be either
            * `discord.Interaction` for app commands and views.
            * `AluContext` for txt commands.
            * `discord.Embed` for custom situations like tasks.
            * `str` for custom situations like tasks.
        where: str
            String to describe where the error happened.
            This is put into log.error message for clearness.
            Also this is put into footer of the embed if the `source` object doesn't clearly represent
            "where" the error has happened.
        extra: str | None
            Extra data string where the whole data can't be described only by just `source` object,
            so it comes externally from the error handler.

            The example of this is error handler in views, where I pass information on view/item objects
            as an extra_data string. This info gets added into extra field in embed.
        """
        log.error("%s: %s.", error.__class__.__name__, where, exc_info=error)

        # apparently there is https://github.com/vi3k6i5/flashtext for "the fastest replacement"
        # not sure if I want to add extra dependance
        traceback_string = "".join(traceback.format_exception(error)).replace(os.getcwd(), "AluBot")
        # .replace("``": "`\u200b`")

        packet = await self.get_info_packet(source=source, where=where, extra=extra)
        # self.errors_cache.setdefault(traceback_string, [info_packet]).append(info_packet)

        async with self._lock:
            if self._most_recent and (delta := packet.dt - self._most_recent) < self.cooldown:
                # We have to wait
                total_seconds = delta.total_seconds()
                log.debug("Waiting %s seconds to send the error.", total_seconds)
                await asyncio.sleep(total_seconds)

            self._most_recent = datetime.datetime.now(datetime.UTC)
            return await self.send_error(traceback_string, packet)


class HandleHTTPException(AbstractAsyncContextManager):
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

    async def __aenter__(self):
        return self

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
