"""
ex_manager.py - yes, it is for managing my exes.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
import traceback
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TYPE_CHECKING, Generator, NamedTuple, Optional, Union

import discord

from config import ERROR_HANDLER_WEBHOOK, TEST_ERROR_HANDLER_WEBHOOK
from utils import AluContext, const, errors

if TYPE_CHECKING:
    from bot import AluBot


log = logging.getLogger('exception_manager')


class ErrorInfoPacket(NamedTuple):
    """
    Parameters
    ----------
    embed: :class: discord.Embed
        embed to send in error notification to the devs
    dt: :class: datetime.datetime
        datetime.datetime to compare for rate-limit purposes
    mention: :class: bool
        whether mention the devs.
        Useful if I'm sitting in debug-spam channel so I don't get unnecessary ping.
    """

    embed: discord.Embed
    dt: datetime.datetime
    mention: bool


class AluExceptionManager:
    """Exception Manager that

    * should be used to send all unhandled errors to developers via webhooks.
    * controls rate-limit of the said webhook
    * contains history of errors that was not fixed yet
    * allows users to track the said errors and get notification when it's fixed
    """

    # Inspired by:
    # licensed MPL v2 from DuckBot-Discord/DuckBot
    # https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/errorhandler.py

    __slots__: tuple[str, ...] = (
        'bot',
        'cooldown',
        'errors_cache',
        '_lock',
        '_most_recent',
        'error_webhook',
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
        self._most_recent: Optional[datetime.datetime] = None

        self.errors_cache: dict[str, list[ErrorInfoPacket]] = {}

        webhook_url = TEST_ERROR_HANDLER_WEBHOOK if self.bot.test else ERROR_HANDLER_WEBHOOK
        self.error_webhook: discord.Webhook = discord.Webhook.from_url(
            url=webhook_url,
            session=bot.session,
            client=bot,
            bot_token=bot.http.token,
        )

    def _yield_code_chunks(self, iterable: str, *, chunks_size: int = 2000) -> Generator[str, None, None]:
        codeblocks: str = '```py\n{}```'
        max_chars_in_code = chunks_size - (len(codeblocks) - 2)  # chunks_size minus code blocker size

        for i in range(0, len(iterable), max_chars_in_code):
            yield codeblocks.format(iterable[i : i + max_chars_in_code])

    async def send_error(self, traceback_string: str, packet: ErrorInfoPacket):
        code_chunks = list(self._yield_code_chunks(traceback_string))

        # hmm, this is honestly a bit too many sends for 5 seconds of rate limit :thinking:
        if packet.mention:
            await self.error_webhook.send(const.Role.error_ping.mention)

        for chunk in code_chunks:
            await self.error_webhook.send(chunk)

        if packet.mention:
            await self.error_webhook.send(embed=packet.embed)

    async def get_info_packet(
        self,
        source: Optional[Union[discord.Interaction[AluBot], AluContext, discord.Embed, str]],
        where: str,
    ) -> ErrorInfoPacket:
        """Get info packet"""

        if isinstance(source, str):
            dt = discord.utils.utcnow()
            e = discord.Embed(colour=0xDA9F93, description=source, timestamp=dt).set_footer(text=where)
            return ErrorInfoPacket(embed=e, dt=dt, mention=True)

        if isinstance(source, discord.Embed):
            if not source.timestamp:
                source.timestamp = dt = discord.utils.utcnow()
            else:
                dt = source.timestamp
            return ErrorInfoPacket(embed=source, dt=dt, mention=True)

        elif isinstance(source, AluContext):
            ctx = source  # I just can't type `source.command.qualified_name` lol

            e = discord.Embed(colour=0x890620, title=f'`{ctx.clean_prefix}{ctx.command}`')
            e.url = ctx.message.jump_url
            e.description = ctx.message.content

            # metadata
            author_text = f'@{ctx.author} triggered error in #{ctx.channel}'
            e.set_author(name=author_text, icon_url=ctx.author.display_avatar)
            if ctx.guild:
                e.set_footer(text=f'{ctx.guild.name}\n{where}', icon_url=ctx.guild.icon)
                guild_id = ctx.guild.id
            else:
                guild_id = 'DM Channel'
                e.set_footer(text=f'DM Channel\n{where}', icon_url=ctx.author.display_avatar)

            # arguments
            args_str = ['```py']
            for name, value in ctx.kwargs.items():
                args_str.append(f'[{name}]: {value!r}')
            else:
                args_str.append('No arguments')
            args_str.append('```')
            e.add_field(name='Command Args', value='\n'.join(args_str), inline=False)
            # ids
            e.add_field(
                name='Snowflake Ids',
                value=(
                    '```py\n'
                    f'author  = {ctx.author.id}\n'
                    f'channel = {ctx.channel.id}\n'
                    f'guild   = {guild_id}\n```'
                ),
            )

            e.timestamp = dt = ctx.message.created_at

            mention = ctx.channel.id != ctx.bot.hideout.spam_channel_id
            return ErrorInfoPacket(embed=e, dt=dt, mention=mention)

        elif isinstance(source, discord.Interaction):
            ntr = source

            e = discord.Embed(colour=0x2C0703)

            app_cmd = ntr.command
            if app_cmd:
                e.title = f'`/{app_cmd.qualified_name}`'
            else:
                e.title = 'Non cmd interaction'

            # metadata
            author_text = f'@{ntr.user} triggered error in #{ntr.channel}'
            e.set_author(name=author_text, icon_url=ntr.user.display_avatar)
            if ntr.guild:
                e.set_footer(text=f'{ntr.guild.name}\n{where}', icon_url=ntr.guild.icon)
                guild_id = ntr.guild.id
            else:
                guild_id = 'DM Channel'
                e.set_footer(text=f'DM Channel\n{where}', icon_url=ntr.user.display_avatar)

            # arguments
            args_str = ['```py']
            for name, value in ntr.namespace.__dict__.items():
                args_str.append(f'[{name}]: {value!r}')
            else:
                args_str.append(f'No arguments')
            args_str.append('```')
            e.add_field(name='Command Args', value='\n'.join(args_str), inline=False)

            # ids
            e.add_field(
                name='Snowflake Ids',
                value=(
                    '```py\n'
                    f'author  = {ntr.user.id}\n'
                    f'channel = {ntr.channel_id}\n'
                    f'guild   = {ntr.guild_id}\n```'
                ),
            )
            e.timestamp = dt = ntr.created_at
            mention = ntr.channel_id != ntr.client.hideout.spam_channel_id
            return ErrorInfoPacket(embed=e, dt=discord.utils.utcnow(), mention=mention)
        else:
            # shouldn't ever trigger
            # probably source is `None`, but let's leave it as "else" for some silly mistake too.
            e = discord.Embed(colour=const.Colour.error())
            e.description = 'Something went wrong somewhere. Please make it so next time it says where here.'
            e.timestamp = dt = discord.utils.utcnow()
            e.set_footer(text=where)
            return ErrorInfoPacket(embed=e, dt=dt, mention=True)

    async def register_error(
        self,
        error: BaseException,
        source: Union[discord.Interaction[AluBot], AluContext, discord.Embed, str],
        *,
        where: str,
    ):
        """Register, analyse error and put it into queue to send to developers

        Parameters
        -----------
        error: :class: Exception
            Exception that the developers of AluBot are going to be notified about
        source: :class: Optional[Union[discord.Interaction[AluBot], AluContext, discord.Embed, str]],
            "source" object of the error. It's basically conditional context
            of where the error happened. Can be either
            * `discord.Interaction` for app commands and views.
            * `AluContext` for txt commands.
            * `discord.Embed` for custom situations like tasks.
            * `str` for custom situations like tasks.
        where: :class: Optional[str]
            string to put into logger.
        """
        log.error('%s: %s.', error.__class__.__name__, where, exc_info=error)

        # apparently there is https://github.com/vi3k6i5/flashtext for "the fastest replacement"
        # not sure if I want to add extra dependance
        traceback_string = "".join(traceback.format_exception(error)).replace(os.getcwd(), 'AluBot')
        # .replace("``": "`\u200b`")

        packet = await self.get_info_packet(source=source, where=where)
        # self.errors_cache.setdefault(traceback_string, [info_packet]).append(info_packet)

        async with self._lock:
            if self._most_recent and (delta := packet.dt - self._most_recent) < self.cooldown:
                # We have to wait
                total_seconds = delta.total_seconds()
                log.debug('Waiting %s seconds to send the error.', total_seconds)
                await asyncio.sleep(total_seconds)

            self._most_recent = discord.utils.utcnow()
            return await self.send_error(traceback_string, packet)


class HandleHTTPException(AbstractAsyncContextManager):
    """Context manger to handle HTTP Exceptions.

    This is useful for handling errors that are not critical, but
    still need to be reported to the user.

    Parameters
    ----------
    destination: :class:`discord.abc.Messageable`
        The destination channel to send the error to.
    title: Optional[:class:`str`]
        The title of the embed. Defaults to ``'An unexpected error occurred!'``.
    """

    __slots__ = ('destination', 'title')

    def __init__(self, destination: discord.abc.Messageable, *, title: Optional[str] = None):
        self.destination = destination
        self.title = title

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> bool:
        if exc_val is not None and isinstance(exc_val, discord.HTTPException) and exc_type:
            embed = discord.Embed(
                title=self.title or 'An unexpected error occurred!',
                description=f'{exc_type.__name__}: {exc_val.text}',
                colour=discord.Colour.red(),
            )

            await self.destination.send(embed=embed)
            raise errors.SilentError

        return False
