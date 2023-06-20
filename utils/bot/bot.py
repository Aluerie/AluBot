from __future__ import annotations

import datetime
import logging
import os
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Union

import discord
from aiohttp import ClientSession
from asyncpg import Pool
from asyncpraw import Reddit
from discord.ext import commands
from dota2.client import Dota2Client
from github import Github
from steam.client import SteamClient

import config
from exts import get_extensions
from utils.imgtools import ImgToolsClient
from utils.jsonconfig import PrefixConfig
from utils.twitch import TwitchClient

from .. import AluContext, ConfirmationView, cache, const, formats
from .cmd_cache import MyCommandTree
from .intents_perms import intents

if TYPE_CHECKING:
    from exts.reminders.reminders import Reminder

    from .. import AluCog, ExtCategory


__all__ = ('AluBot',)

log = logging.getLogger(__name__)


class AluBot(commands.Bot):
    if TYPE_CHECKING:
        bot_app_info: discord.AppInfo
        dota: Dota2Client
        github: Github
        imgtools: ImgToolsClient
        launch_time: datetime.datetime
        logging_handler: Any
        session: ClientSession
        pool: Pool
        prefixes: PrefixConfig
        reddit: Reddit
        steam: SteamClient
        tree: MyCommandTree
        twitch: TwitchClient
        user: discord.ClientUser

        cogs: Mapping[str, AluCog]

    def __init__(self, test=False):
        main_prefix = '~' if test else '$'
        self.main_prefix = main_prefix
        super().__init__(
            command_prefix=self.get_pre,
            activity=discord.Streaming(name=f"\N{PURPLE HEART} /help /setup", url='https://www.twitch.tv/aluerie'),
            intents=intents,
            allowed_mentions=discord.AllowedMentions(roles=True, replied_user=False, everyone=False),  # .none()
            tree_cls=MyCommandTree,
        )
        self.client_id: int = config.TEST_DISCORD_CLIENT_ID if test else config.DISCORD_CLIENT_ID
        self.test: bool = test
        self.odota_ratelimit: Dict[str, int] = {'monthly': -1, 'minutely': -1}

        self.repo = 'https://github.com/Aluerie/AluBot'
        self.developer = 'Aluerie'

        # modules
        self.config = config
        self.formats = formats

        self.ext_categories: Dict[Optional[ExtCategory], List[AluCog]] = {}

        self.mimic_message_user_mapping: MutableMapping[int, int] = cache.ExpiringCache(
            timedelta=datetime.timedelta(days=7)
        )

    async def setup_hook(self) -> None:
        self.session = s = ClientSession()
        self.imgtools = ImgToolsClient(session=s)

        self.prefixes = PrefixConfig(self.pool)
        self.bot_app_info = await self.application_info()

        # ensure temp folder
        # TODO: maybe remove the concept of temp folder - don't save .mp3 file
        #  for now it is only used in tts.py for mp3 file
        Path("./.temp/").mkdir(parents=True, exist_ok=True)

        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"  # need to be before loading jsk

        for ext in get_extensions(self.test):
            try:
                await self.load_extension(ext)
            except Exception as error:
                msg = f'Failed to load extension {ext}.'
                log.exception(msg)
                await self.send_exception(error, from_where=msg)

    def get_pre(self, bot: AluBot, message: discord.Message) -> Iterable[str]:
        if message.guild is None:
            prefix = self.main_prefix
        else:
            prefix = self.prefixes.get(message.guild.id, self.main_prefix)
        return commands.when_mentioned_or(prefix, "/")(bot, message)

    async def add_cog(self, cog: AluCog):
        await super().add_cog(cog)

        self.ext_categories.setdefault(cog.category, []).append(cog)

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
                steam_login, steam_password = (
                    config.TEST_STEAM_USERNAME,
                    config.TEST_STEAM_PASSWORD,
                )
            else:
                steam_login, steam_password = (
                    config.STEAM_USERNAME,
                    config.STEAM_PASSWORD,
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
            self.github = Github(config.GIT_PERSONAL_TOKEN)

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

    @discord.utils.cached_property
    def error_webhook(self) -> discord.Webhook:
        if self.test:
            url = config.TEST_ERROR_HANDLER_WEBHOOK_URL
        else:
            url = config.ERROR_HANDLER_WEBHOOK_URL

        hook = discord.Webhook.from_url(url=url, session=self.session)
        return hook

    async def send_exception(
        self,
        exception: BaseException,
        *,
        embed: Optional[discord.Embed] = None,
        from_where: Optional[str] = None,
        mention: bool = True,
        include_traceback: bool = True,
    ) -> None:
        """
        Send exception and its traceback to notify me via Discord webhook

        Parameters
        -----------
        error: :class: Exception
            Exception that the developers of AluBot are going to be notified about
        embed: :class: discord.Embed
            discord.Embed object to prettify the output with extra info
            Note that specifiying embed will foreshadow `from_where` value.
        from_where: :class: str
            If there is no need for custom embed but you just want to attach
            a simple string string telling where error has happened then you use `from_where`
        mention: :class: bool
            if `True` then the message will mention the bot developer
        include_traceback: :class: bool
            Whether include the traceback into the messages.
        """
        if from_where is not None and embed is not None:
            raise TypeError('Cannot mix `from_where` and `embed` keyword arguments.')
        if from_where is None and embed is None:
            from_where = '`from_where` was not specified.'
            # raise TypeError('Key arguments `from_where` and `embed` cannot be `None` at the same time.')

        hook = self.error_webhook
        try:
            if mention:
                await hook.send(const.Role.error_ping.mention)
            if include_traceback:
                traceback_content = "".join(traceback.format_exception(exception))

                paginator = commands.Paginator(prefix='```py')
                for line in traceback_content.split('\n'):
                    paginator.add_line(line)

                for page in paginator.pages:
                    await hook.send(page)

            e = embed or discord.Embed(colour=const.Colour.error()).set_author(name=from_where)
            await hook.send(embed=e)
        except Exception as error:
            log.info(error)

    async def send_traceback(
        self,
        error: Exception,
        *,
        where: str = 'not specified',
        embed: Optional[discord.Embed] = None,
        verbosity: int = 10,
        mention: bool = True,
    ) -> None:
        """Function to send traceback into the discord channel.

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

        Returns
        --------
        None
        """
        # TODO: remove this function in favour of new send_exception

        etype, value, trace = type(error), error, error.__traceback__
        traceback_content = "".join(traceback.format_exception(etype, value, trace, verbosity)).replace(
            "``", "`\u200b`"
        )

        paginator = commands.Paginator(prefix='```py')
        for line in traceback_content.split('\n'):
            paginator.add_line(line)

        e = embed or discord.Embed(colour=const.Colour.error()).set_author(name=where)
        content = self.owner.mention if mention else ''

        wh = self.error_webhook
        await wh.send(content=content, embed=e)

        for page in paginator.pages:
            await wh.send(page)

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
