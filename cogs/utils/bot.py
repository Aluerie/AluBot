from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from os import environ, listdir
from typing import (
    TYPE_CHECKING, Any, Union, Dict, Optional, Tuple, List, Sequence, Protocol
)

from asyncpg import Pool
from aiohttp import ClientSession
from asyncpraw import Reddit
from discord import Streaming, Intents, AllowedMentions, Embed
from discord.ext import commands
from dota2.client import Dota2Client
from github import Github
from steam.client import SteamClient
from tweepy.asynchronous import AsyncClient as TwitterAsyncClient

import config as cfg
from . import imgtools
from .config import PrefixConfig
from .context import Context
from .twitch import TwitchClient
from .var import Sid, Cid, Clr, umntn, Uid

if TYPE_CHECKING:
    from asyncpg import Connection
    from discord import AppInfo, File, Interaction, Message, User
    from discord.app_commands import AppCommand
    from discord.abc import Snowflake, Messageable
    from github import Repository
    from types import TracebackType

log = logging.getLogger(__name__)

try:
    from tlist import test_list
except ModuleNotFoundError:
    test_list = []


def _alubot_prefix_callable(bot: AluBot, msg: Message):
    if msg.guild is None:
        prefix = '$'
    else:
        prefix = bot.prefixes.get(msg.guild.id, '$')
    return commands.when_mentioned_or(prefix, "/")(bot, msg)


# For typing purposes, `AluBot.db` returns a Protocol type
# that allows us to properly type the return values via narrowing
# Right now, `asyncpg` is untyped so this is better than the current status quo
# To actually receive the regular `Pool` type `AluBot.pool` can be used instead.


class ConnectionContextManager(Protocol):
    async def __aenter__(self) -> Connection:
        ...

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        ...


class DatabaseProtocol(Protocol):
    async def execute(self, query: str, *args: Any, timeout: Optional[float] = None) -> str:
        ...

    async def fetch(self, query: str, *args: Any, timeout: Optional[float] = None) -> list[Any]:
        ...

    async def fetchrow(self, query: str, *args: Any, timeout: Optional[float] = None) -> Optional[Any]:
        ...

    async def fetchval(self, query: str, *args: Any, timeout: Optional[float] = None) -> Optional[Any]:
        ...

    def acquire(self, *, timeout: Optional[float] = None) -> ConnectionContextManager:
        ...

    def release(self, connection: Connection) -> None:
        ...


class AluBot(commands.Bot):
    bot_app_info: AppInfo
    steam: SteamClient
    dota: Dota2Client
    github: Github
    git_gameplay: Repository.Repository
    git_tracker: Repository.Repository
    session: ClientSession
    launch_time: datetime
    pool: Pool
    prefixes: PrefixConfig
    reddit: Reddit
    twitch: TwitchClient
    twitter: TwitterAsyncClient

    def __init__(self, test=False):
        prefix = commands.when_mentioned_or('~') if test else _alubot_prefix_callable
        main_prefix = '~' if test else '$'
        super().__init__(
            command_prefix=prefix,
            activity=Streaming(
                name=f"/help or {main_prefix}help",
                url='https://www.twitch.tv/aluerie'
            ),
            intents=Intents(  # if you ever struggle with it - try `Intents.all()`
                guilds=True,
                members=True,
                bans=True,
                emojis_and_stickers=True,
                voice_states=True,
                presences=True,
                messages=True,
                reactions=True,
                message_content=True
            ),
            allowed_mentions=AllowedMentions(
                roles=True,
                replied_user=False,
                everyone=False
            )  # .none()
        )
        self.client_id: str = cfg.TEST_DISCORD_CLIENT_ID if test else cfg.DISCORD_CLIENT_ID
        self.test: bool = test
        self.app_commands: Dict[str, int] = {}
        self.odota_ratelimit: str = 'was not received yet'

    async def setup_hook(self) -> None:
        self.session = ClientSession()
        self.prefixes = PrefixConfig(self.pool)
        self.bot_app_info = await self.application_info()

        environ["JISHAKU_NO_UNDERSCORE"] = "True"
        environ["JISHAKU_HIDE"] = "True"  # need to be before loading jsk
        extensions_list = ['jishaku']
        if self.test and len(test_list):
            extensions_list += [f'cogs.{name}' for name in test_list]
        else:
            extensions_list += [f'cogs.{filename[:-3]}' for filename in listdir('./cogs') if filename.endswith('.py')]

        for ext in extensions_list:
            try:
                await self.load_extension(ext)
            except Exception as e:
                log.exception(f'Failed to load extension {ext}.')
                raise e

    async def on_ready(self):
        if not hasattr(self, 'launch_time'):
            self.launch_time = datetime.now(timezone.utc)
        log.info(f'Logged in as {self.user}')

    async def close(self) -> None:
        await super().close()
        if hasattr(self, 'session'):
            await self.session.close()
        if hasattr(self, 'twitch'):
            await self.twitch.close()

    async def my_start(self) -> None:
        token = cfg.TEST_TOKEN if self.test else cfg.MAIN_TOKEN
        await super().start(token, reconnect=True)

    async def get_context(self, origin: Union[Interaction, Message], /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    @property
    def db(self) -> DatabaseProtocol:
        return self.pool  # type: ignore

    @property
    def owner(self) -> User:
        return self.bot_app_info.owner

    def ini_steam_dota(self) -> None:
        if not hasattr(self, 'steam') or not hasattr(self, 'dota'):
            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            self.steam_dota_login()

    def steam_dota_login(self) -> None:
        if self.steam.connected is False:
            log.debug(f"dota2info: client.connected {self.steam.connected}")
            if self.test:
                steam_login, steam_password = (cfg.STEAM_TEST_LGN, cfg.STEAM_TEST_PSW,)
            else:
                steam_login, steam_password = (cfg.STEAM_MAIN_LGN, cfg.STEAM_MAIN_PSW,)

            if self.steam.login(username=steam_login, password=steam_password):
                self.steam.change_status(persona_state=7)
                log.info('We successfully logged invis mode into Steam')
                self.dota.launch()
            else:
                log.warning('Logging into Steam failed')
                return

    def ini_github(self) -> None:
        if not hasattr(self, 'github'):
            self.github = Github(cfg.GIT_PERSONAL_TOKEN)
            self.git_gameplay = self.github.get_repo("ValveSoftware/Dota2-Gameplay")
            self.git_tracker = self.github.get_repo("SteamDatabase/GameTracking-Dota2")

    def ini_reddit(self) -> None:
        if not hasattr(self, 'reddit'):
            self.reddit = Reddit(
                client_id=cfg.REDDIT_CLIENT_ID,
                client_secret=cfg.REDDIT_CLIENT_SECRET,
                password=cfg.REDDIT_PASSWORD,
                user_agent=cfg.REDDIT_USER_AGENT,
                username=cfg.REDDIT_USERNAME
            )

    async def ini_twitch(self) -> None:
        if not hasattr(self, 'twitch'):
            self.twitch = TwitchClient(cfg.TWITCH_TOKEN)
            await self.twitch.connect()

    def ini_twitter(self) -> None:
        if not hasattr(self, 'twitter'):
            self.twitter = TwitterAsyncClient(cfg.TWITTER_BEARER_TOKEN)

    def get_app_command(
            self,
            value: Union[str, int]
    ) -> Optional[Tuple[str, int]]:

        for cmd_name, cmd_id in self.app_commands.items():
            if value == cmd_name or value.isdigit() and int(value) == cmd_id:
                return cmd_name, cmd_id

        return None

    async def update_app_commands_cache(
            self,
            *,
            cmds: Optional[List[AppCommand]] = None,
            guild: Optional[Snowflake] = None
    ) -> None:
        if not cmds:
            cmds = await self.tree.fetch_commands(guild=guild.id if guild else None)
        self.app_commands = {cmd.name: cmd.id for cmd in cmds}

    # Shortcuts

    @property
    def alu_guild(self):
        return self.get_guild(Sid.alu)

    @property
    def wink_guild(self):
        return self.get_guild(Sid.wink)

    @property
    def blush_guild(self):
        return self.get_guild(Sid.blush)

    # Image Tools
    @staticmethod
    def str_to_file(
            string: str,
            filename: str = "FromAluBot.txt"
    ) -> File:
        return imgtools.str_to_file(string, filename)

    @staticmethod
    def plt_to_file(
            fig,
            filename: str = 'FromAluBot.png'
    ) -> File:
        return imgtools.plt_to_file(fig, filename)

    @staticmethod
    def img_to_file(
            image,
            filename: str = 'FromAluBot.png',
            fmt: str = 'PNG'
    ) -> File:
        return imgtools.img_to_file(image, filename, fmt)

    async def url_to_img(
            self,
            url: Union[str, Sequence[str]],
            *,
            return_list: bool = False
    ):
        return await imgtools.url_to_img(self.session, url, return_list=return_list)

    async def url_to_file(
            self,
            url: Union[str, Sequence[str]],
            filename: str = 'FromAluBot.png',
            *,
            return_list: bool = False
    ) -> Union[File, Sequence[File]]:
        return await imgtools.url_to_file(self.session, url, filename, return_list=return_list)

    def update_odota_ratelimit(self, headers) -> None:
        monthly = headers.get('X-Rate-Limit-Remaining-Month')
        minutely = headers.get('X-Rate-Limit-Remaining-Minute')
        if monthly is not None or minutely is not None:
            self.odota_ratelimit = f'monthly: {monthly}, minutely: {minutely}'

    async def send_traceback(
            self,
            error: Exception,
            destination: Optional[Messageable] = None,
            *,
            where: str = 'not specified',
            embed: Optional[Embed] = None,
            verbosity: int = 10,
            mention: bool = True
    ) -> None:
        """
        Function to send traceback into the discord channel.

        It pings @Irene if non-testing version of the bot is running.
        @param error:
        @param destination:
        @param where:
        if `embed` is specified then this is ignored essentially
        @param embed:
        @param verbosity:
        @param mention:
        @return: None
        """
        ch = destination or self.get_channel(Cid.spam_me)

        etype, value, trace = type(error), error, error.__traceback__
        traceback_content = "".join(
            traceback.format_exception(etype, value, trace, verbosity)
        ).replace("``", "`\u200b`")

        paginator = commands.Paginator(prefix='```python')
        for line in traceback_content.split('\n'):
            paginator.add_line(line)

        embed = embed or Embed(colour=Clr.error).set_author(name=where)
        content = umntn(Uid.alu) if mention else ''
        await ch.send(content=content, embed=embed)

        for page in paginator.pages:
            await ch.send(page)


#########################################
#      Logging magic starts here        #
#########################################
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
import discord.utils


class MyColourFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[37;1m%(asctime)s\x1b[0m | {colour}%(levelname)-7s\x1b[0m | '
            f'\x1b[35m%(name)-23s\x1b[0m | %(lineno)-4d | %(funcName)-30s | %(message)s',
            '%H:%M:%S %d/%m',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def get_log_fmt(
        handler: logging.Handler
):
    if isinstance(handler, logging.StreamHandler) and discord.utils.stream_supports_colour(handler.stream)\
            and not isinstance(handler, RotatingFileHandler):  # force file handler fmt into `else`
        formatter = MyColourFormatter()
    else:
        formatter = logging.Formatter(
            '{asctime} | {levelname:<7} | {name:<23} | {lineno:<4} | {funcName:<30} | {message}',
            '%H:%M:%S %d/%m', style='{'
        )

    return formatter


@contextmanager
def setup_logging(test: bool):
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    try:
        # Stream Handler
        handler = logging.StreamHandler()
        handler.setFormatter(get_log_fmt(handler))
        log.addHandler(handler)

        # File Handler
        file_handler = RotatingFileHandler(
            filename='alubot.log' if not test else 'alubot_test.log',
            encoding='utf-8',
            mode='w',
            maxBytes=16 * 1024 * 1024,  # 16 MiB
            backupCount=5  # Rotate through 5 files
        )
        file_handler.setFormatter(get_log_fmt(file_handler))
        log.addHandler(file_handler)

        yield
    finally:
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)
