from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Iterable, Literal, MutableMapping, Union

import discord
from discord.ext import commands

import config
from extensions import get_extensions
from utils import EXT_CATEGORY_NONE, AluContext, ExtCategory, cache, const, formats
from utils.disambiguator import Disambiguator
from utils.jsonconfig import PrefixConfig
from utils.transposer import TransposeClient

from .app_cmd_tree import AluAppCommandTree
from .exc_manager import AluExceptionManager
from .intents_perms import intents, permissions
from .timer import TimerManager

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool

    from utils import AluCog


__all__ = ("AluBot",)

log = logging.getLogger(__name__)


class AluBotHelper(TimerManager):
    """Extra class to help with MRO Nerdge"""

    def __init__(self, *, bot: AluBot) -> None:
        super().__init__(bot=bot)


class AluBot(commands.Bot, AluBotHelper):
    if TYPE_CHECKING:
        user: discord.ClientUser
        #     bot_app_info: discord.AppInfo
        #     launch_time: datetime.datetime
        logging_handler: Any
        #     prefixes: PrefixConfig
        tree: AluAppCommandTree
        #     cogs: Mapping[str, AluCog]
        old_tree_error: Callable[
            [discord.Interaction[AluBot], discord.app_commands.AppCommandError], Coroutine[Any, Any, None]
        ]

    def __init__(self, test=False, *, session: ClientSession, pool: Pool, **kwargs: Any):
        main_prefix = "~" if test else "$"
        self.main_prefix: Literal["~", "$"] = main_prefix
        self.test: bool = test
        super().__init__(
            command_prefix=self.get_pre,
            activity=discord.Streaming(name=f"\N{PURPLE HEART} /help /setup", url="https://www.twitch.tv/aluerie"),
            intents=intents,
            allowed_mentions=discord.AllowedMentions(roles=True, replied_user=False, everyone=False),  # .none()
            tree_cls=AluAppCommandTree,
        )
        self.pool: Pool = pool
        self.session: ClientSession = session

        self.exc_manager: AluExceptionManager = AluExceptionManager(self)
        self.transposer: TransposeClient = TransposeClient(session=session)
        self.disambiguator: Disambiguator = Disambiguator()

        self.repo_url = "https://github.com/Aluerie/AluBot"
        self.developer = "Aluerie"  # it's my GitHub account name
        self.server_url = "https://discord.gg/K8FuDeP"

        # modules
        self.formats = formats

        self.category_cogs: dict[ExtCategory, list[AluCog | commands.Cog]] = dict()

        self.mimic_message_user_mapping: MutableMapping[int, int] = cache.ExpiringCache(
            seconds=datetime.timedelta(days=7).seconds
        )

    async def setup_hook(self) -> None:
        self.prefixes = PrefixConfig(self.pool)
        self.bot_app_info = await self.application_info()

        # ensure temp folder
        Path("./.alubot/temp/").mkdir(parents=True, exist_ok=True)

        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"  # need to be before loading jsk

        failed = False
        for ext in get_extensions(self.test):
            try:
                await self.load_extension(ext)
            except Exception as error:
                failed = True
                msg = f"Failed to load extension `{ext}`."
                await self.exc_manager.register_error(error, msg, where=msg)

        # we could go with attribute option like exceptions manager
        # but let's keep its methods nearby
        # needs to be done after cogs are loaded so all cog event listeners are ready
        super(AluBotHelper, self).__init__(bot=self)

        if self.test:

            async def try_auto_sync_with_logging():
                try:
                    result = await self.try_hideout_auto_sync()
                except Exception as err:
                    log.error("Autosync: failed %s.", const.Tick.no, exc_info=err)
                else:
                    if result:
                        log.info("Autosync: success %s.", const.Tick.yes)
                    else:
                        log.info("Autosync: not needed %s.", const.Tick.black)

            if not failed:
                self.loop.create_task(try_auto_sync_with_logging())
            else:
                log.info("Autosync: cancelled %s One or more cogs failed to load.", const.Tick.no)

    async def try_hideout_auto_sync(self) -> bool:
        """Try auto copy-global+sync for hideout guild."""

        # Inspired by:
        # licensed MPL v2 from DuckBot-Discord/DuckBot `try_autosync``
        # https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/bot.py

        # tag ass, and all. But strictly for convenient development purposes.
        # let's try min-maxing auto-sync in my hideout/debug guild in my test bot.

        # safeguard. Need the app id.
        await self.wait_until_ready()

        guild = discord.Object(id=self.hideout.id)
        self.tree.copy_global_to(guild=guild)

        all_cmds = self.tree._get_all_commands(guild=guild)

        new_payloads = [(guild.id, cmd.to_dict()) for cmd in all_cmds]

        query = "SELECT payload FROM auto_sync WHERE guild_id = $1"
        db_payloads = [r["payload"] for r in await self.pool.fetch(query, guild.id)]

        updated_payloads = [p for _, p in new_payloads if p not in db_payloads]
        outdated_payloads = [p for p in db_payloads if p not in [p for _, p in new_payloads]]
        not_synced = updated_payloads + outdated_payloads

        if not_synced:
            await self.pool.execute("DELETE FROM auto_sync WHERE guild_id = $1", guild.id)
            await self.pool.executemany("INSERT INTO auto_sync (guild_id, payload) VALUES ($1, $2)", new_payloads)

            await self.tree.sync(guild=guild)
            return True
        else:
            return False

    def get_pre(self, bot: AluBot, message: discord.Message) -> Iterable[str]:
        if message.guild is None:
            prefix = self.main_prefix
        else:
            prefix = self.prefixes.get(message.guild.id, self.main_prefix)
        return commands.when_mentioned_or(prefix, "/")(bot, message)

    async def add_cog(self, cog: AluCog | commands.Cog):
        await super().add_cog(cog)

        # jishaku does not have a category thus we have this weird typehint
        category = getattr(cog, "category", None)
        if not category or not isinstance(category, ExtCategory):
            category = EXT_CATEGORY_NONE

        self.category_cogs.setdefault(category, []).append(cog)

    async def on_ready(self):
        if not hasattr(self, "launch_time"):
            self.launch_time = datetime.datetime.now(datetime.timezone.utc)
        log.info(f"Logged in as {self.user}")

    async def my_start(self) -> None:
        token = config.TEST_TOKEN if self.test else config.MAIN_TOKEN
        # token = cfg.MAIN_TOKEN
        await super().start(token, reconnect=True)

    async def get_context(
        self, origin: Union[discord.Interaction, discord.Message], /, *, cls=AluContext
    ) -> AluContext:
        return await super().get_context(origin, cls=cls)

    @property
    def owner(self) -> discord.User:
        return self.bot_app_info.owner

    # INITIALIZE EXTRA ATTRIBUTES/CLIENTS/FUNCTIONS ####################################################################

    # The following functions are `initialize_something`
    # which import some heavy modules and initialize some ~heavy clients under bot namespace
    # they should be used in `__init__` or in `cog_load` only for those cogs which need to work with them,
    # i.e. fpc dota notifications should call
    # `bot.initialize_steam_dota`, `bot.initialize_opendota` and `bot.initialize_twitch`
    # This is done exclusively so when I run only a few cogs on testing bot - I don't need to load all modules/clients.
    #
    # note that I import inside the functions which is against pep8 but apparently it is not so bad:
    # pep8 answer: https://stackoverflow.com/a/1188672/19217368
    # points to import inside the function: https://stackoverflow.com/a/1188693/19217368
    # and I exactly want these^

    async def initialize_dota_pulsefire_clients(self) -> None:
        """Initialize Dota 2 pulsefire-like clients

        * OpenDota API pulsefire client
        * Stratz API pulsefire client
        """
        if not hasattr(self, "opendota_client"):
            from utils.dota import OpenDotaClient, StratzClient

            self.opendota_client = OpenDotaClient()
            await self.opendota_client.__aenter__()

            self.stratz_client = StratzClient()
            await self.stratz_client.__aenter__()

    def initialize_dota_cache(self) -> None:
        """Initialize Dota 2 constants cache

        * OpenDota Dota Constants cache with static data
        """
        if not hasattr(self, "dota_cache"):
            from utils.dota import DotaCache

            self.dota_cache = DotaCache(self)

    async def initialize_league_pulsefire_clients(self) -> None:
        """Initialize League Of Legends pulsefire clients

        * Riot API Pulsefire client
        * CDragon Pulsefire client
        """

        if not hasattr(self, "riot_api_client"):
            import orjson
            from pulsefire.clients import CDragonClient, RiotAPIClient
            from pulsefire.middlewares import http_error_middleware, json_response_middleware, rate_limiter_middleware
            from pulsefire.ratelimiters import RiotAPIRateLimiter  # cSpell: ignore ratelimiters

            self.riot_api_client = RiotAPIClient(
                default_headers={"X-Riot-Token": config.RIOT_API_KEY},
                middlewares=[
                    json_response_middleware(orjson.loads),
                    http_error_middleware(),
                    rate_limiter_middleware(RiotAPIRateLimiter()),
                ],
            )
            await self.riot_api_client.__aenter__()

            self.cdragon_client = CDragonClient(
                default_params={"patch": "latest", "locale": "default"},
                middlewares=[
                    json_response_middleware(orjson.loads),
                    http_error_middleware(),
                ],
            )
            await self.cdragon_client.__aenter__()

    def initialize_league_cache(self) -> None:
        """Initialize League of Legends caches

        * CDragon Cache with static game data
        * MerakiAnalysis Cache with roles identification data
        """

        if not hasattr(self, "cdragon"):
            from utils.lol import CDragonCache, MerakiRolesCache

            self.cdragon = CDragonCache(self)
            self.meraki_roles = MerakiRolesCache(self)

    async def initialize_steam_dota(self) -> None:
        """Initialize Steam and Dota 2 Clients
        
        * Dota 2 Client, allows communicating with Dota 2 Game Coordinator
        * Steam Client, necessary step to login in for Dota 2.^
        """
        if not hasattr(self, "steam"):
            from dota2.client import Dota2Client
            from steam.client import SteamClient

            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            await self.login_into_steam_dota()

            @self.steam.on("disconnected")  # type: ignore
            def try_to_reconnect_on_disconnect():
                self.steam.reconnect()

            @self.steam.on("error")  # type: ignore
            def try_to_reconnect_on_error(error_result):
                self.steam.reconnect()

    async def login_into_steam_dota(self) -> None:
        """Login into Steam and Launch Dota 2."""
        log.debug("Checking if steam is connected: %s", self.steam.connected)
        if self.steam.connected is False:
            log.debug(f"dota2info: client.connected {self.steam.connected}")
            if self.test:
                steam_login, steam_password = (config.TEST_STEAM_USERNAME, config.TEST_STEAM_PASSWORD)
            else:
                steam_login, steam_password = (config.STEAM_USERNAME, config.STEAM_PASSWORD)

            try:
                if self.steam.login(username=steam_login, password=steam_password):
                    self.steam.change_status(persona_state=7)
                    log.info("We successfully logged invis mode into Steam: %s", steam_login)
                    self.dota.launch()
            except Exception as exc:
                log.error("Logging into Steam failed")
                await self.exc_manager.register_error(exc, source="steam login", where="steam login")

    def initialize_github(self) -> None:
        """Initialize GitHub REST API Client"""
        if not hasattr(self, "github"):
            from githubkit import GitHub

            self.github = GitHub(config.GIT_PERSONAL_TOKEN)

    async def initialize_twitch(self) -> None:
        """Initialize subclassed twitchio's Twitch Client."""
        if not hasattr(self, "twitch"):
            from utils.twitch import TwitchClient

            self.twitch = TwitchClient(self)
            await self.twitch.connect()

    def initialize_tz_manager(self) -> None:
        """Initialize TimeZone Manager."""
        if not hasattr(self, "tz_manager"):
            from utils.timezones import TimezoneManager

            self.tz_manager = TimezoneManager(self)

    async def close(self) -> None:
        """Closes the connection to Discord while cleaning up other open sessions and clients."""
        await super().close()
        if hasattr(self, "session"):
            await self.session.close()
        if hasattr(self, "twitch"):
            await self.twitch.close()
        if hasattr(self, "riot_api_client"):
            await self.riot_api_client.__aexit__()
        if hasattr(self, "cdragon_client"):
            await self.cdragon_client.__aexit__()
        if hasattr(self, "opendota_client"):
            await self.opendota_client.__aexit__()

    @property
    def hideout(self) -> const.HideoutGuild:
        """Shortcut to get Hideout guild, its channels and roles."""
        return const.HideoutGuild(self)

    @property
    def community(self) -> const.CommunityGuild:
        """Shortcut to get Community guild, its channels and roles."""
        return const.CommunityGuild(self)

    @discord.utils.cached_property
    def invite_link(self) -> str:
        """Get invite link for the bot."""
        return discord.utils.oauth_url(
            self.user.id,
            permissions=permissions,
            scopes=("bot", "applications.commands"),
        )
