from __future__ import annotations

import contextlib
import datetime
import logging
import os
from typing import TYPE_CHECKING, Any, Literal, override

import discord
from discord.ext import commands
from discord.utils import MISSING

import config
from ext import get_extensions
from utils import EXT_CATEGORY_NONE, AluContext, ExtCategory, cache, const
from utils.disambiguator import Disambiguator
from utils.transposer import TransposeClient

from .app_cmd_tree import AluAppCommandTree
from .exc_manager import ExceptionManager
from .intents_perms import INTENTS, PERMISSIONS
from .timer import TimerManager

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, MutableMapping, Sequence

    import asyncpg
    from aiohttp import ClientSession
    from discord.abc import Snowflake

    from utils import AluCog
    from utils.database import DotRecord, PoolTypedWithAny


__all__ = ("AluBot",)

log = logging.getLogger(__name__)


class AluBotHelper(TimerManager):
    """Extra class to help with MRO."""

    def __init__(self, *, bot: AluBot) -> None:
        super().__init__(bot=bot)


class AluBot(commands.Bot, AluBotHelper):
    """AluBot."""

    if TYPE_CHECKING:
        user: discord.ClientUser
        #     bot_app_info: discord.AppInfo
        #     launch_time: datetime.datetime
        logging_handler: Any
        #     prefixes: PrefixConfig
        tree: AluAppCommandTree
        #     cogs: Mapping[str, AluCog]
        old_tree_error: Callable[
            [discord.Interaction[AluBot], discord.app_commands.AppCommandError],
            Coroutine[Any, Any, None],
        ]
        command_prefix: set[Literal["~", "$"]]  # default is some mix of Iterable[str] and Callable
        listener_connection: asyncpg.Connection[DotRecord]

    def __init__(
        self, test: bool = False, *, session: ClientSession, pool: asyncpg.Pool[DotRecord], **kwargs: Any
    ) -> None:
        self.test: bool = test
        self.main_prefix: Literal["~", "$"] = "~" if test else "$"

        super().__init__(
            command_prefix={self.main_prefix},
            activity=discord.Streaming(
                name="\N{PURPLE HEART} /help /setup",
                url="https://www.twitch.tv/irene_adler__",
            ),
            intents=INTENTS,
            allowed_mentions=discord.AllowedMentions(roles=True, replied_user=False, everyone=False),  # .none()
            tree_cls=AluAppCommandTree,
            strip_after_prefix=True,
            case_insensitive=True,
        )
        self.database: asyncpg.Pool[DotRecord] = pool
        self.pool: PoolTypedWithAny = pool  # type: ignore # asyncpg typehinting crutch, read `utils.database` for more
        self.session: ClientSession = session

        self.exc_manager: ExceptionManager = ExceptionManager(self)
        self.transposer: TransposeClient = TransposeClient(session=session)
        self.disambiguator: Disambiguator = Disambiguator()

        self.repo_url: str = "https://github.com/Aluerie/AluBot"
        self.developer: str = "Aluerie"  # it's my GitHub account name
        self.server_url: str = "https://discord.gg/K8FuDeP"

        self.category_cogs: dict[ExtCategory, list[AluCog]] = {}

        self.mimic_message_user_mapping: MutableMapping[int, int] = cache.ExpiringCache(
            seconds=datetime.timedelta(days=7).seconds
        )

        self.prefix_cache: dict[int, set[str]] = {}

    @override
    async def setup_hook(self) -> None:
        self.bot_app_info: discord.AppInfo = await self.application_info()

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

        await self.populate_database_cache()
        await self.create_database_listeners()

        # we could go with attribute option like exceptions manager
        # but let's keep its methods nearby in AluBot namespace
        # needs to be done after cogs are loaded so all cog event listeners are ready
        super(AluBotHelper, self).__init__(bot=self)

        if self.test:

            async def try_auto_sync_with_logging() -> None:
                try:
                    result = await self.try_hideout_auto_sync()
                except Exception as err:
                    log.error("Autosync: failed %s.", const.Tick.No, exc_info=err)
                else:
                    if result:
                        log.info("Autosync: success %s.", const.Tick.Yes)
                    else:
                        log.info("Autosync: not needed %s.", const.Tick.Black)

            if not failed:
                self.loop.create_task(try_auto_sync_with_logging())
            else:
                log.info(
                    "Autosync: cancelled %s One or more cogs failed to load.",
                    const.Tick.No,
                )

    async def try_hideout_auto_sync(self) -> bool:
        """Try auto copy-global+sync for hideout guild."""
        # Inspired by:
        # licensed MPL v2 from DuckBot-Discord/DuckBot `try_autosync`
        # https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/bot.py

        # tag ass, and all. But strictly for convenient development purposes.
        # let's try min-maxing auto-sync in my hideout/debug guild in my test bot.

        # safeguard. Need the app id.
        await self.wait_until_ready()

        guild = discord.Object(id=self.hideout.id)
        self.tree.copy_global_to(guild=guild)

        all_cmds = self.tree.get_commands(guild=guild)

        new_payloads = [(guild.id, cmd.to_dict()) for cmd in all_cmds]

        query = "SELECT payload FROM auto_sync WHERE guild_id = $1"
        db_payloads = [r["payload"] for r in await self.pool.fetch(query, guild.id)]

        updated_payloads = [p for _, p in new_payloads if p not in db_payloads]
        outdated_payloads = [p for p in db_payloads if p not in [p for _, p in new_payloads]]
        not_synced = updated_payloads + outdated_payloads

        if not_synced:
            await self.pool.execute("DELETE FROM auto_sync WHERE guild_id = $1", guild.id)
            await self.pool.executemany(
                "INSERT INTO auto_sync (guild_id, payload) VALUES ($1, $2)",
                new_payloads,
            )

            await self.tree.sync(guild=guild)
            return True
        else:
            return False

    async def populate_database_cache(self) -> None:
        """Populate cache coming from the database."""
        prefix_data: list[tuple[int, set[str]]] = await self.pool.fetch("SELECT guild_id, prefixes FROM guilds")
        self.prefix_cache = {guild_id: prefixes for guild_id, prefixes in prefix_data if prefixes}

    @override
    async def get_prefix(self, message: discord.Message) -> list[str]:
        """Return the prefixes for the given message.

        Parameters
        ----------
        message : discord.Message
            The message to get the prefix of.

        """
        cached_prefixes = self.prefix_cache.get((message.guild and message.guild.id or 0), None)
        base_prefixes = set(cached_prefixes) if cached_prefixes else self.command_prefix
        return commands.when_mentioned_or(*base_prefixes)(self, message)

    async def create_database_listeners(self) -> None:
        """Register listeners for database events."""
        self.listener_connection = await self.pool.acquire()  # type: ignore

        async def _delete_prefixes_event(
            conn: asyncpg.Connection[DotRecord], pid: int, channel: str, payload: str
        ) -> None:
            from_json = discord.utils._from_json(payload)
            with contextlib.suppress(Exception):
                del self.prefix_cache[from_json["guild_id"]]

        async def _create_or_update_event(
            conn: asyncpg.Connection[DotRecord], pid: int, channel: str, payload: str
        ) -> None:
            from_json = discord.utils._from_json(payload)
            self.prefix_cache[from_json["guild_id"]] = set(from_json["prefixes"])

        # they want `conn` in functions above to be type-hinted as
        # `asyncpg.Connection[Any] | asyncpg.pool.PoolConnectionProxy[Any]`
        # and payload as `object`
        # while we define those params very clearly in .sql and here.
        await self.listener_connection.add_listener("delete_prefixes", _delete_prefixes_event)  # type: ignore
        await self.listener_connection.add_listener("update_prefixes", _create_or_update_event)  # type: ignore

    @override
    async def add_cog(
        self,
        cog: AluCog,
        /,
        *,
        override: bool = False,
        guild: Snowflake | None = MISSING,
        guilds: Sequence[Snowflake] = MISSING,
    ) -> None:
        await super().add_cog(cog, override=override, guild=guild, guilds=guilds)

        # jishaku does not have a category thus we have this weird typehint
        category = getattr(cog, "category", None)
        if not category or not isinstance(category, ExtCategory):
            category = EXT_CATEGORY_NONE

        self.category_cogs.setdefault(category, []).append(cog)

    async def on_ready(self) -> None:
        """Handle `ready` event."""
        if not hasattr(self, "launch_time"):
            self.launch_time = datetime.datetime.now(datetime.UTC)
        # if hasattr(self, "dota"):
        #     await self.dota.wait_until_ready()
        log.info("Logged in as `%s`", self.user)

    @override
    async def start(self) -> None:
        token = config.TEST_TOKEN if self.test else config.MAIN_TOKEN

        # erm, bcs of my horrendous .test logic we need to do it in a weird way
        # todo: is there anything better ? :D

        # if not self.test or "ext.fpc.dota" in get_extensions(self.test):
        #     from utils.dota.dota2client import Dota2Client

        #     self.dota = Dota2Client(self)
        #     await asyncio.gather(
        #         super().start(token, reconnect=True),
        #         self.dota.login(),
        #     )
        # else:
        await super().start(token, reconnect=True)  # VALVE_SWITCH

    @override
    async def get_context(self, origin: discord.Interaction | discord.Message) -> AluContext:
        return await super().get_context(origin, cls=AluContext)

    @property
    def owner(self) -> discord.User:
        """Get bot's owner user."""
        return self.bot_app_info.owner

    # INITIALIZE EXTRA ATTRIBUTES/CLIENTS/FUNCTIONS

    # The following functions are `initialize_something`
    # which import some heavy modules and initialize some ~heavy clients under bot namespace
    # they should be used in `__init__` or in `cog_load` methods in cog classes that need to work with them,
    # i.e. fpc dota notifications should call
    # `bot.initialize_dota`, `bot.initialize_dota_cache`, `bot.initialize_twitch`, etc.
    # This is done exclusively so when I run only a few cogs on test bot
    # I don't need to load those heavy modules/clients.
    #
    # note that I import inside the functions which is against pep8 but apparently it is not so bad:
    # pep8 answer: https://stackoverflow.com/a/1188672/19217368
    # points to import inside the function: https://stackoverflow.com/a/1188693/19217368
    # and I exactly want these^

    async def initialize_dota_pulsefire_clients(self) -> None:
        """Initialize Dota 2 pulsefire-like clients.

        * OpenDota API pulsefire client
        * Stratz API pulsefire client
        """
        if not hasattr(self, "opendota"):
            from utils.dota import ODotaConstantsClient, OpenDotaClient, StratzClient

            self.opendota = OpenDotaClient()
            await self.opendota.__aenter__()

            self.stratz = StratzClient()
            await self.stratz.__aenter__()

            self.odota_constants = ODotaConstantsClient()
            await self.odota_constants.__aenter__()

    def initialize_cache_dota(self) -> None:
        """Initialize Dota 2 constants cache.

        * OpenDota Dota Constants cache with static data
        """
        if not hasattr(self, "cache_dota"):
            from utils.dota import CacheDota

            self.cache_dota = CacheDota(self)

    async def initialize_league_pulsefire_clients(self) -> None:
        """Initialize League Of Legends pulsefire clients.

        * Riot API Pulsefire client
        * CDragon Pulsefire client
        * Meraki Pulsefire client
        """
        if not hasattr(self, "riot"):
            import orjson
            from pulsefire.clients import CDragonClient, MerakiCDNClient, RiotAPIClient
            from pulsefire.middlewares import http_error_middleware, json_response_middleware, rate_limiter_middleware
            from pulsefire.ratelimiters import RiotAPIRateLimiter

            self.riot = RiotAPIClient(
                default_headers={"X-Riot-Token": config.RIOT_API_KEY},
                middlewares=[
                    json_response_middleware(orjson.loads),
                    http_error_middleware(),
                    rate_limiter_middleware(RiotAPIRateLimiter()),
                ],
            )
            await self.riot.__aenter__()

            self.cdragon = CDragonClient(
                default_params={"patch": "latest", "locale": "default"},
                middlewares=[
                    json_response_middleware(orjson.loads),
                    http_error_middleware(),
                ],
            )
            await self.cdragon.__aenter__()

            self.meraki = MerakiCDNClient(
                middlewares=[
                    json_response_middleware(orjson.loads),
                    http_error_middleware(),
                ],
            )
            await self.meraki.__aenter__()

    def initialize_cache_league(self) -> None:
        """Initialize League of Legends caches.

        * CDragon Cache with static game data
        * MerakiAnalysis Cache with roles identification data
        """
        if not hasattr(self, "cache_lol"):
            from utils.lol import CacheLoL

            self.cache_lol = CacheLoL(self)

    # async def initialize_dota(self) -> None:
    #     """Initialize Dota 2 Client

    #     * Dota 2 Client, allows communicating with Dota 2 Game Coordinator and Steam
    #     """
    #     if not hasattr(self, "dota"):
    #         from utils.dota.dota2client import Dota2Client

    #         self.dota = Dota2Client(self)
    #         await self.dota.login()

    async def initialize_dota(self) -> None:
        """Initialize Dota 2 Client.

        * Dota 2 Client, allows communicating with Dota 2 Game Coordinator and Steam
        """
        if not hasattr(self, "dota"):
            from utils.dota.valvepythondota2 import Dota2Client

            self.dota = Dota2Client(self)
            await self.dota.login()

    def initialize_github(self) -> None:
        """Initialize GitHub REST API Client."""
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

    @override
    async def close(self) -> None:
        """Close the connection to Discord while cleaning up other open sessions and clients."""
        await super().close()
        # if hasattr(self, "dota"):
        #     await self.dota.close() # VALVE SWITCH
        if hasattr(self, "session"):
            await self.session.close()
        if hasattr(self, "twitch"):
            await self.twitch.close()

        # things to __aexit__()
        for client in [
            "riot",
            "cdragon",
            "meraki",
            "opendota",
            "stratz",
            "odota_constants",
        ]:
            if hasattr(self, client):
                await getattr(self, client).__aexit__()

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
            permissions=PERMISSIONS,
            scopes=("bot", "applications.commands"),
        )
