from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Iterable, Mapping, MutableMapping, Optional, Union

import discord
from asyncpraw import Reddit
from discord.ext import commands
from dota2.client import Dota2Client
from githubkit import GitHub
from steam.client import SteamClient

import config
from extensions import get_extensions
from utils import AluContext, ConfirmationView, ExtCategory, cache, const, formats, none_category
from utils.imgtools import ImgToolsClient
from utils.jsonconfig import PrefixConfig
from utils.twitch import TwitchClient

from .app_cmd_tree import AluAppCommandTree
from .exc_manager import AluExceptionManager
from .intents_perms import intents, permissions

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool

    from extensions.reminders.reminders import Reminder
    from utils import AluCog


__all__ = ('AluBot',)

log = logging.getLogger(__name__)


class AluBot(commands.Bot):
    if TYPE_CHECKING:
        bot_app_info: discord.AppInfo
        dota: Dota2Client
        github: GitHub
        launch_time: datetime.datetime
        logging_handler: Any
        prefixes: PrefixConfig
        reddit: Reddit
        steam: SteamClient
        tree: AluAppCommandTree
        twitch: TwitchClient
        user: discord.ClientUser
        cogs: Mapping[str, AluCog]
        old_tree_error: Callable[
            [discord.Interaction[AluBot], discord.app_commands.AppCommandError], Coroutine[Any, Any, None]
        ]

    def __init__(self, test=False, *, session: ClientSession, pool: Pool, **kwargs):
        main_prefix = '~' if test else '$'
        self.main_prefix = main_prefix
        self.test: bool = test
        super().__init__(
            command_prefix=self.get_pre,
            activity=discord.Streaming(name=f"\N{PURPLE HEART} /help /setup", url='https://www.twitch.tv/aluerie'),
            intents=intents,
            allowed_mentions=discord.AllowedMentions(roles=True, replied_user=False, everyone=False),  # .none()
            tree_cls=AluAppCommandTree,
            case_insensitive=True,  # todo: this isn't applied to command groups; maybe make new base class?
        )
        self.pool: Pool = pool
        self.session: ClientSession = session

        self.exc_manager: AluExceptionManager = AluExceptionManager(self)
        self.imgtools = ImgToolsClient(session=session)

        self.odota_ratelimit: dict[str, int] = {'monthly': -1, 'minutely': -1}

        self.repo_url = 'https://github.com/Aluerie/AluBot'
        self.developer = 'Aluerie'  # it's my GitHub account name
        self.server_url = 'https://discord.gg/K8FuDeP'

        # modules
        self.formats = formats

        self.category_cogs: dict[ExtCategory, list[AluCog | commands.Cog]] = dict()

        self.mimic_message_user_mapping: MutableMapping[int, int] = cache.ExpiringCache(
            timedelta=datetime.timedelta(days=7)
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
                msg = f'Failed to load extension `{ext}`.'
                await self.exc_manager.register_error(error, msg, where=msg)

        if self.test:

            async def try_auto_sync_with_logging():
                try:
                    result = await self.try_hideout_auto_sync()
                except Exception as err:
                    log.error('Autosync: failed %s.', const.Tick.no, exc_info=err)
                else:
                    if result:
                        log.info('Autosync: success %s.', const.Tick.yes)
                    else:
                        log.info('Autosync: not needed %s.', const.Tick.black)

            if not failed:
                self.loop.create_task(try_auto_sync_with_logging())
            else:
                log.info('Autosync: cancelled %s One or more cogs failed to load.', const.Tick.no)

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

        query = 'SELECT payload FROM auto_sync WHERE guild_id = $1'
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
        category = getattr(cog, 'category', None)
        if not category or not isinstance(category, ExtCategory):
            category = none_category

        self.category_cogs.setdefault(category, []).append(cog)

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

    def ini_steam_dota(self) -> None:
        if not hasattr(self, 'steam') or not hasattr(self, 'dota'):
            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            self.steam_dota_login()

    def steam_dota_login(self) -> None:
        if self.steam.connected is False:
            log.debug(f"dota2info: client.connected {self.steam.connected}")
            if self.test:
                steam_login, steam_password = (config.TEST_STEAM_USERNAME, config.TEST_STEAM_PASSWORD)
            else:
                steam_login, steam_password = (config.STEAM_USERNAME, config.STEAM_PASSWORD)

            if self.steam.login(username=steam_login, password=steam_password):
                self.steam.change_status(persona_state=7)
                log.info('We successfully logged invis mode into Steam')
                self.dota.launch()
            else:
                log.warning('Logging into Steam failed')
                return

    def ini_github(self) -> None:
        if not hasattr(self, 'github'):
            self.github = GitHub(config.GIT_PERSONAL_TOKEN)

    def ini_reddit(self) -> None:
        if not hasattr(self, 'reddit'):
            self.reddit = Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                password=config.REDDIT_PASSWORD,
                user_agent=config.REDDIT_USER_AGENT,
                username=config.REDDIT_USERNAME,
            )

    async def ini_twitch(self) -> None:
        if not hasattr(self, 'twitch'):
            self.twitch = TwitchClient(config.TWITCH_TOKEN)
            await self.twitch.connect()

    def update_odota_ratelimit(self, headers) -> None:
        monthly = headers.get('X-Rate-Limit-Remaining-Month')
        minutely = headers.get('X-Rate-Limit-Remaining-Minute')
        if monthly is not None or minutely is not None:
            self.odota_ratelimit = {'monthly': monthly, 'minutely': minutely}

    @property
    def reminder(self) -> Optional[Reminder]:
        return self.get_cog('Reminder')  # type: ignore

    async def prompt(
        self,
        ctx_ntr: AluContext | discord.Interaction[AluBot],
        *,
        content: str = discord.utils.MISSING,
        embed: discord.Embed = discord.utils.MISSING,
        timeout: float = 100.0,
        delete_after: bool = False,
        author_id: Optional[int] = None,
    ) -> Optional[bool]:
        """
        An interactive reaction confirmation dialog.
        Parameters
        -----------
        content: str
            Text message to show along with the prompt.
        embed:
            Embed to show along with the prompt.
        timeout: float
            How long to wait before returning.
        delete_after: bool
            Whether to delete the confirmation message after we're done.
        author_id: Optional[int]
            The member who should respond to the prompt. Defaults to the author of the
            Context's message.
        Returns
        --------
        Optional[bool]
            ``True`` if explicit confirm,
            ``False`` if explicit deny,
            ``None`` if deny due to timeout
        ----
        """
        if content is None and embed is None:
            raise TypeError('Either content or embed should be provided')

        author_id = author_id or ctx_ntr.user.id
        view = ConfirmationView(timeout=timeout, delete_after=delete_after, author_id=author_id)
        if isinstance(ctx_ntr, AluContext):
            view.message = await ctx_ntr.reply(content=content, embed=embed, view=view)
        elif isinstance(ctx_ntr, discord.Interaction):
            if not ctx_ntr.response.is_done():
                view.message = await ctx_ntr.response.send_message(content=content, embed=embed, view=view)
            else:
                view.message = await ctx_ntr.followup.send(content=content, embed=embed, view=view)
        await view.wait()
        return view.value

    @property
    def hideout(self) -> const.HideoutGuild:
        return const.HideoutGuild(self)

    @property
    def community(self) -> const.CommunityGuild:
        return const.CommunityGuild(self)

    @discord.utils.cached_property
    def invite_link(self) -> str:
        return discord.utils.oauth_url(
            self.user.id,
            permissions=permissions,
            scopes=("bot", "applications.commands"),
        )