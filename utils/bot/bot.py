from __future__ import annotations

import datetime
import logging
import os
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Union

import discord
from aiohttp import ClientSession
from asyncpg import Pool
from asyncpraw import Reddit
from discord.ext import commands
from dota2.client import Dota2Client
from github import Github
from steam.client import SteamClient
from tweepy.asynchronous import AsyncClient as TwitterAsyncClient

import config as cfg
from cogs import get_extensions
from utils import AluContext, const
from utils.imgtools import ImgToolsClient
from utils.jsonconfig import PrefixConfig
from utils.twitch import TwitchClient

from .cmd_cache import MyCommandTree

if TYPE_CHECKING:
    from cogs.reminders import Reminder


__all__ = ('AluBot',)

log = logging.getLogger(__name__)


class AluBot(commands.Bot):
    bot_app_info: discord.AppInfo
    dota: Dota2Client
    github: Github
    imgtools: ImgToolsClient
    launch_time: datetime.datetime
    session: ClientSession
    pool: Pool
    prefixes: PrefixConfig
    reddit: Reddit
    steam: SteamClient
    tree: MyCommandTree
    twitch: TwitchClient
    twitter: TwitterAsyncClient
    user: discord.ClientUser

    def __init__(self, test=False):
        main_prefix = '~' if test else '$'
        self.main_prefix = main_prefix
        super().__init__(
            command_prefix=self.get_pre,
            activity=discord.Streaming(name=f"\N{PURPLE HEART} /help /setup", url='https://www.twitch.tv/aluerie'),
            intents=discord.Intents(  # if you ever struggle with it - try `discord.Intents.all()`
                guilds=True,
                members=True,
                bans=True,
                emojis_and_stickers=True,
                voice_states=True,
                presences=True,
                messages=True,
                reactions=True,
                message_content=True,
            ),
            allowed_mentions=discord.AllowedMentions(roles=True, replied_user=False, everyone=False),  # .none()
            tree_cls=MyCommandTree,
        )
        self.client_id: int = cfg.TEST_DISCORD_CLIENT_ID if test else cfg.DISCORD_CLIENT_ID
        self.test: bool = test
        self.app_commands: Dict[str, int] = {}
        self.odota_ratelimit: Dict[str, int] = {'monthly': -1, 'minutely': -1}

        self.repo = 'https://github.com/Aluerie/AluBot'
        self.developer = 'Aluerie'

    async def setup_hook(self) -> None:
        self.session = s = ClientSession()
        self.imgtools = ImgToolsClient(session=s)

        self.prefixes = PrefixConfig(self.pool)
        self.bot_app_info = await self.application_info()

        # ensure temp folder
        # todo: maybe remove the concept of temp folder - don't save .mp3 file
        #  for now it is only used in tts.py for mp3 file
        Path("./.temp/").mkdir(parents=True, exist_ok=True)

        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"  # need to be before loading jsk

        for ext in get_extensions(self.test):
            try:
                await self.load_extension(ext)
            except Exception as e:
                log.exception(f'Failed to load extension {ext}.')

    def get_pre(self, bot: AluBot, message: discord.Message) -> Iterable[str]:
        if message.guild is None:
            prefix = self.main_prefix
        else:
            prefix = self.prefixes.get(message.guild.id, self.main_prefix)
        return commands.when_mentioned_or(prefix, "/")(bot, message)

    async def on_ready(self):
        if not hasattr(self, 'launch_time'):
            self.launch_time = discord.utils.utcnow()
        log.info(f'Logged in as {self.user}')

    async def close(self) -> None:
        await super().close()
        if hasattr(self, 'session'):
            await self.session.close()
        if hasattr(self, 'twitch'):
            pass
            await self.twitch.close()

    async def my_start(self) -> None:
        token = cfg.TEST_TOKEN if self.test else cfg.MAIN_TOKEN
        # token = cfg.MAIN_TOKEN
        await super().start(token, reconnect=True)

    async def get_context(
        self, origin: Union[discord.Interaction, discord.Message], /, *, cls=AluContext
    ) -> AluContext:
        return await super().get_context(origin, cls=cls)

    @property
    def owner(self) -> discord.User:
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
                steam_login, steam_password = (
                    cfg.STEAM_TEST_LGN,
                    cfg.STEAM_TEST_PSW,
                )
            else:
                steam_login, steam_password = (
                    cfg.STEAM_MAIN_LGN,
                    cfg.STEAM_MAIN_PSW,
                )

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

    def ini_reddit(self) -> None:
        if not hasattr(self, 'reddit'):
            self.reddit = Reddit(
                client_id=cfg.REDDIT_CLIENT_ID,
                client_secret=cfg.REDDIT_CLIENT_SECRET,
                password=cfg.REDDIT_PASSWORD,
                user_agent=cfg.REDDIT_USER_AGENT,
                username=cfg.REDDIT_USERNAME,
            )

    async def ini_twitch(self) -> None:
        if not hasattr(self, 'twitch'):
            self.twitch = TwitchClient(cfg.TWITCH_TOKEN)
            await self.twitch.connect()

    def ini_twitter(self) -> None:
        if not hasattr(self, 'twitter'):
            self.twitter = TwitterAsyncClient(cfg.TWITTER_BEARER_TOKEN)

    def update_odota_ratelimit(self, headers) -> None:
        monthly = headers.get('X-Rate-Limit-Remaining-Month')
        minutely = headers.get('X-Rate-Limit-Remaining-Minute')
        if monthly is not None or minutely is not None:
            self.odota_ratelimit = {'monthly': monthly, 'minutely': minutely}

    @property
    def reminder(self) -> Optional[Reminder]:
        return self.get_cog('Reminder')  # type: ignore

    async def send_traceback(
        self,
        error: Exception,
        destination: Optional[discord.TextChannel] = None,
        *,
        where: str = 'not specified',
        embed: Optional[discord.Embed] = None,
        verbosity: int = 10,
        mention: bool = True,
    ) -> None:
        """Function to send traceback into the discord channel.
        Parameters
        -----------
        error: :class: Exception
            Exception that is going to be sent to the `destination`
        destination:
            where to send the traceback message
        where:
            Just a text prompt to include into the default embed
            about where exactly error happened
            if `embed` is specified then this is ignored essentially
        embed:
            When specifying `where` is not enough
            you can make the whole embed instead of using default embed `where`
        verbosity:
            A parameter for `traceback.format_exception()`
        mention: bool
            if True then the message will mention the bot owner
        Returns
        --------
        None
        """

        ch: discord.TextChannel = destination or self.hideout.spam

        etype, value, trace = type(error), error, error.__traceback__
        traceback_content = "".join(traceback.format_exception(etype, value, trace, verbosity)).replace(
            "``", "`\u200b`"
        )

        paginator = commands.Paginator(prefix='```python')
        for line in traceback_content.split('\n'):
            paginator.add_line(line)

        e = embed or discord.Embed(colour=const.Colour.error()).set_author(name=where)
        content = self.owner.mention if mention else ''
        await ch.send(content=content, embed=e)

        for page in paginator.pages:
            await ch.send(page)

    # SHORTCUTS ########################################################################################################

    @property
    def hideout(self) -> const.HideoutGuild:
        return const.HideoutGuild(self)

    @property
    def community(self) -> const.CommunityGuild:
        return const.CommunityGuild(self)
