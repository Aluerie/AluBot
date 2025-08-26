from __future__ import annotations

import asyncio
import datetime
import logging
import sys
import textwrap
from typing import TYPE_CHECKING, Any, Literal, override

import discord
from discord.ext import commands

from bot import AluContext
from config import config
from ext import get_extensions
from utils import cache, const, disambiguator, errors, fmt, helpers, transposer

from .exc_manager import ExceptionManager
from .intents_perms import INTENTS, PERMISSIONS
from .timer_manager import TimerManager
from .tree import AluAppCommandTree

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    import asyncpg
    from aiohttp import ClientSession

    from bot import AluInteraction
    from types_.database import PoolTypedWithAny


__all__ = ("AluBot",)

log = logging.getLogger(__name__)


class AluBot(commands.Bot):
    """Main class for AluBot.

    Essentially extended subclass over discord.py's `commands.Bot`
    Used to interact with the Discord WebSocket, API and more.
    Includes discord.py's `ext.commands` extension to organize cogs/commands framework.
    """

    if TYPE_CHECKING:
        command_prefix: set[Literal["~", "$"]]  # default is some mix of Iterable[str] and Callable
        launch_time: datetime.datetime
        listener_connection: asyncpg.Connection[asyncpg.Record]
        logs_via_webhook_handler: Any
        tree: AluAppCommandTree
        user: discord.ClientUser

    def __init__(
        self,
        *,
        test: bool = False,
        session: ClientSession,
        pool: asyncpg.Pool[asyncpg.Record],
    ) -> None:
        """Initialize the AluBot.

        Parameters
        ----------
        test: bool = False
            whether the bot is a testing version (YenBot) or main production bot (AluBot).
            I just like to use different discord bot token to debug issues, test new code, etc.
        session: ClientSession
            aiohttp.ClientSession to use within the bot.
        pool: asyncpg.Pool[asyncpg.Record]
            A connection pool to the database.

        """
        self.test: bool = test
        self.main_prefix: Literal["~", "$"] = "~" if test else "$"

        super().__init__(
            command_prefix={self.main_prefix},
            activity=discord.Streaming(name="\N{PURPLE HEART} /help /setup", url="https://twitch.tv/irene_adler__"),
            intents=INTENTS,
            allowed_mentions=discord.AllowedMentions(roles=True, replied_user=False, everyone=False),  # .none()
            tree_cls=AluAppCommandTree,
            strip_after_prefix=True,
            case_insensitive=True,
            help_command=None,
        )
        self.extensions_to_load: tuple[str, ...] = get_extensions(test=self.test)
        # asyncpg typehinting crutch, read `utils.database` for more
        self.pool: PoolTypedWithAny = pool  # pyright:ignore[reportAttributeAccessIssue]
        self.session: ClientSession = session

        self.exc_manager: ExceptionManager = ExceptionManager(self)
        self.transposer: transposer.TransposeClient = transposer.TransposeClient(session=session)
        self.disambiguator: disambiguator.Disambiguator = disambiguator.Disambiguator()

        self.repository_url: str = "https://github.com/Aluerie/AluBot"
        self.developer: str = "Aluerie"  # it's my GitHub account name
        self.community_invite_url: str = "https://discord.gg/K8FuDeP"

        # self.help_categories: dict[ExtCategory, list[AluCog]] = {}  # TODO:???
        self.mimic_messages: MutableMapping[int, int] = cache.ExpiringCache(seconds=datetime.timedelta(days=7).seconds)
        """Mapping of `message_id -> user_id` for Mimic Messages."""

    @override
    async def setup_hook(self) -> None:
        self.bot_app_info: discord.AppInfo = await self.application_info()

        failed_to_load_some_ext = False
        for ext in self.extensions_to_load:
            try:
                await self.load_extension(ext)
            except commands.ExtensionError as error:
                failed_to_load_some_ext = True
                embed = discord.Embed(color=0xDA9F93, description=f"Failed to load extension `{ext}`.").set_footer(
                    text=f'setup_hook: loading extension "{ext}"'
                )
                await self.exc_manager.register_error(error, embed)

        # we could go with attribute option like exceptions manager
        # but let's keep its methods nearby in AluBot namespace
        # needs to be done after cogs are loaded so all cog event listeners are ready
        self.timers = TimerManager(bot=self)

        if self.test:
            if failed_to_load_some_ext:
                log.info("Autosync: cancelled %s One or more cogs failed to load.", const.Tick.No)
            else:
                self.loop.create_task(self.try_hideout_auto_sync_with_logging())

    async def try_hideout_auto_sync_with_logging(self) -> None:
        """Helper function to wrap `try_hideout_auto_sync` `into try/except` block with some logging."""
        try:
            result = await self.try_hideout_auto_sync()
        except Exception as err:
            log.exception("Autosync: failed %s.", const.Tick.No, exc_info=err)
        else:
            phrase = f"success {const.Tick.Yes}" if result else f"not needed {const.Tick.Black}"
            log.info("Autosync: %s.", phrase)

    async def try_hideout_auto_sync(self) -> bool:
        """Try automatic `copy_global_to` + `sync` Hideout Guild for easier testing purposes.

        ?tag ass (auto-syncing sucks) and all, but come on - it's just too convenient to pass on.
        The function is using non-global sync methods so should be fine on rate-limits.

        Sources
        -------
        * DuckBot-Discord/DuckBot (licensed MPL v2), `try_autosync` function
            https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/bot.py
        """
        # safeguard. Need the app id.
        await self.wait_until_ready()

        guild = discord.Object(id=self.hideout.id)
        self.tree.copy_global_to(guild=guild)

        all_cmds = self.tree.get_commands(guild=guild)

        new_payloads = [(guild.id, cmd.to_dict(self.tree)) for cmd in all_cmds]

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
        return False

    async def on_ready(self) -> None:
        """Handle `ready` event."""
        if not hasattr(self, "launch_time"):
            self.launch_time = datetime.datetime.now(datetime.UTC)
        log.info("Logged in as `%s`", self.user)
        if not self.test:
            await self.send_warning("AluBot is ready.")

    @override
    async def start(self) -> None:
        discord_token = config["DISCORD"]["ALUBOT"] if not self.test else config["DISCORD"]["YENBOT"]
        coroutines = [super().start(discord_token, reconnect=True)]

        dota_extensions = (
            "ext.dota",
            "ext.dota.fpc_notifications",
            # "ext.beta",  # uncomment when we are testing dota-related stuff in `ext.beta`
        )
        if any(ext in self.extensions_to_load for ext in dota_extensions):
            self.instantiate_dota()
            coroutines.append(self.dota.login())

        await asyncio.gather(*coroutines)

    @override
    async def get_context(self, origin: AluInteraction | discord.Message) -> AluContext:
        return await super().get_context(origin, cls=AluContext)

    @property
    def owner(self) -> discord.User:
        """Get bot's owner user."""
        return self.bot_app_info.owner

    """
    Instantiate Functions
    ---------------------
    The following functions are `instantiate_something`
    which import some heavy modules and instantiate some ~heavy clients under bot's namespace.
    They should be used in `__init__` or in `cog_load` methods in cog classes that require them,
    i.e. fpc dota notifications should call `bot.initialize_dota`, `bot.instantiate_twitch`.
    This is done exclusively so when I run only a few cogs with a test bot -
    I don't need to load those heavy modules/clients.

    Note, that while I import inside the functions which is against PEP-8 - apparently it is not so bad:
    * pep8 answer: https://stackoverflow.com/a/1188672/19217368
    * points to import inside the function: https://stackoverflow.com/a/1188693/19217368
    and I exactly want these^
    """

    def instantiate_lol(self) -> None:
        """Instantiate League of Legends Client."""
        if not hasattr(self, "lol"):
            from ext.lol.api import LeagueClient

            self.lol = LeagueClient(self)

    def instantiate_dota(self) -> None:
        """Instantiate Dota 2 Client.

        * Dota 2 Client, allows communicating with Dota 2 Game Coordinator and Steam
        """
        if not hasattr(self, "dota"):
            from ext.dota.api.steamio_client import DotaClient

            self.dota = DotaClient(self)

    def instantiate_github(self) -> None:
        """Initialize GitHub REST API Client."""
        if not hasattr(self, "github"):
            from githubkit import GitHub

            self.github = GitHub(config["TOKENS"]["GIT_PERSONAL"])

    async def instantiate_twitch(self) -> None:
        """Instantiate subclassed twitchio's Twitch Client."""
        if not hasattr(self, "twitch"):
            from utils.twitch import AluTwitchClient

            self.twitch = AluTwitchClient(self)
            await self.twitch.login()

    def instantiate_tz_manager(self) -> None:
        """Instantiate TimeZone Manager."""
        if not hasattr(self, "tz_manager"):
            from utils.timezones import TimezoneManager

            self.tz_manager = TimezoneManager(self)

    @override
    async def close(self) -> None:
        """Close the connection to Discord while cleaning up other open sessions and clients."""
        log.info("%s is closing.", self.__class__.__name__)
        if not self.test:
            await self.send_warning("AluBot is closing.")

        await self.pool.close()
        if hasattr(self, "twitch"):
            await self.twitch.close()
        if hasattr(self, "dota"):
            await self.dota.close()
        if hasattr(self, "lol"):
            await self.lol.close()

        await super().close()
        # session needs to be closed the last probably
        if hasattr(self, "session"):
            await self.session.close()

    @property
    def hideout(self) -> const.HideoutGuild:
        """Shortcut for Hideout guild, its channels and roles."""
        return const.HideoutGuild(self)

    @property
    def community(self) -> const.CommunityGuild:
        """Shortcut for Community guild, its channels and roles."""
        return const.CommunityGuild(self)

    @discord.utils.cached_property
    def invite_link(self) -> str:
        """Get invite link for the bot."""
        return discord.utils.oauth_url(self.user.id, permissions=PERMISSIONS, scopes=("bot", "applications.commands"))

    def webhook_from_url(self, url: str) -> discord.Webhook:
        """A shortcut function with filled in discord.Webhook.from_url arguments."""
        return discord.Webhook.from_url(
            url=url,
            session=self.session,
            client=self,
            bot_token=self.http.token,
        )

    async def webhook_from_database(self, channel_id: int) -> discord.Webhook:
        """Fetch webhook_url from the database by the `channel_id`."""
        query = "SELECT url FROM webhooks WHERE channel_id = $1"
        webhook_url: str | None = await self.pool.fetchval(query, channel_id)
        if webhook_url:
            return self.webhook_from_url(webhook_url)
        msg = f"There is no webhook in the database for channel with id={channel_id}"
        raise errors.PlaceholderError(msg)

    @discord.utils.cached_property
    def spam_webhook(self) -> discord.Webhook:
        """A shortcut to spam webhook."""
        webhook_url = config["WEBHOOKS"]["SPAM"] if not self.test else config["WEBHOOKS"]["YEN_SPAM"]
        return self.webhook_from_url(webhook_url)

    async def send_warning(self, message: str, *, mention: bool = False) -> None:
        """Send a quick warning embed to @Aluerie's spam channel."""
        content = const.Role.warning.mention if mention else ""
        embed = discord.Embed(color=discord.Color.yellow(), description=message)
        await self.spam_webhook.send(content=content, embed=embed)

    @discord.utils.cached_property
    def error_webhook(self) -> discord.Webhook:
        """A shortcut to error webhook."""
        webhook_url = config["WEBHOOKS"]["ERROR"] if not self.test else config["WEBHOOKS"]["YEN_ERROR"]
        return self.webhook_from_url(webhook_url)

    @discord.utils.cached_property
    def error_ping(self) -> str:
        """A short for @Error role ping in the hideout."""
        return const.Role.error.mention if not self.test else const.Role.test_error.mention

    @override
    async def on_message(self, message: discord.Message) -> None:
        """A bot's listener for processing commands from discord messages that the bot can see.

        Currently, the bot doesn't allow text command anywhere except my secret hideout server.
        People should use slash commands. Some remaining text commands are dev-only.

        Note that this doesn't change behavior of other "on_message" listeners,
        i.e. they will still listen to messages from all guilds.
        """
        if message.guild and message.guild.id == const.Guild.hideout and not message.author.bot:
            # only process commands in my own private server and only from me (the only non-bot account in there);
            # everybody else everywhere else should use slash commands.
            await self.process_commands(message)

    @override
    async def on_error(self: AluBot, event: str, *args: Any, **kwargs: Any) -> None:
        """Called when an error is raised in an event listener.

        Parameters
        ----------
        event: str
            The name of the event that raised the exception.
        args: Any
            The positional arguments for the event that raised the exception.
        kwargs: Any
            The keyword arguments for the event that raised the exception.

        """
        (_exception_type, exception, _traceback) = sys.exc_info()
        if exception is None:
            exception = TypeError("Somehow `on_error` fired with exception being `None`.")

        args_join = "\n".join(f"[{index}]: {arg!r}" for index, arg in enumerate(args)) if args else "No Args"
        embed = (
            discord.Embed(color=0xA32952, title=f"Event Error: `{event}`")
            .add_field(name="Args", value=fmt.code(args_join, "ps"), inline=False)
            .set_footer(text=f"{self.__class__.__name__}.on_error: {event}")
        )
        await self.exc_manager.register_error(exception, embed)

    @override
    async def on_command_error(self, ctx: AluContext, error: commands.CommandError | Exception) -> None:
        """Handler called when an error is raised while invoking a ctx command.

        In case of problems - check out on_command_error in parent BotBase class - it's not simply `pass`
        """
        if ctx.is_error_handled is True:
            return

        # error handler working variables
        desc = "No description"
        is_unexpected = False

        # error handler itself.

        if isinstance(error, commands.CommandInvokeError):
            # we aren't interested in the chain traceback.
            # commands.HybridCommandError() if we ever bring back hybrid commands;
            error = error.original

        match error:
            # MY OWN ERRORS
            case errors.AluBotError():
                # These errors are generally raised in code by myself or by my code with an explanation text as `error`
                # AluBotError subclassed exceptions are all mine.
                desc = f"{error}"

            # UserInputError SUBCLASSED ERRORS
            case commands.BadLiteralArgument():
                desc = (
                    f"Sorry! Incorrect argument value: {error.argument!r}.\n Only these options are valid "
                    f"for a parameter `{error.param.displayed_name or error.param.name}`:\n"
                    f"{fmt.human_join([repr(literal) for literal in error.literals])}."
                )

            case commands.EmojiNotFound():
                desc = f"Sorry! `{error.argument}` is not a custom emote."
            case commands.BadArgument():
                desc = f"{error}"

            case commands.MissingRequiredArgument():
                desc = f"Please, provide this argument:\n`{error.param.name}`"
            case commands.CommandNotFound():
                if ctx.prefix in {"/", f"<@{ctx.bot.user.id}> ", f"<@!{ctx.bot.user.id}> "}:
                    return
                if ctx.prefix == "$" and ctx.message.content[1].isdigit():
                    # "$200 for this?" 2 is `ctx.message.content[1]`
                    # prefix commands should not start with digits
                    return
                # TODO: make a fuzzy search in here to recommend the command that user wants
                desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
            case commands.CommandOnCooldown():
                desc = f"Please retry in `{fmt.human_timedelta(error.retry_after, mode='brief')}`"
            case commands.NotOwner():
                desc = f"Sorry, only {ctx.bot.owner} as the bot developer is allowed to use this command."
            case commands.MissingRole():
                desc = f"Sorry, only {error.missing_role} are able to use this command."
            case commands.CheckFailure():
                desc = f"{error}"
            case _:
                # error is unhandled/unclear and thus developers need to be notified about it.
                is_unexpected = True

                cmd_name = f"{ctx.clean_prefix}{ctx.command.qualified_name if ctx.command else 'non-cmd'}"
                kwargs_join = (
                    "\n".join(f"[{name}]: {value!r}" for name, value in ctx.kwargs.items())
                    if ctx.kwargs
                    else "No arguments"
                )
                snowflake_ids = (
                    f"author  = {ctx.author.id}\n"
                    f"channel = {ctx.channel.id}\n"
                    f"guild   = {ctx.guild.id if ctx.guild else 'DM Channel'}"
                )
                metadata_embed = (
                    discord.Embed(
                        color=0x890620,
                        title=f"Ctx Command Error: `{ctx.clean_prefix}{ctx.command}`",
                        url=ctx.message.jump_url,
                        description=textwrap.shorten(ctx.message.content, width=1024),
                    )
                    .set_author(
                        name=f"@{ctx.author} in #{ctx.channel} ({ctx.guild.name if ctx.guild else 'DM Channel'})",
                        icon_url=ctx.author.display_avatar,
                    )
                    .add_field(name="Command Args", value=fmt.code(kwargs_join, "ps"), inline=False)
                    .add_field(name="Snowflake IDs", value=fmt.code(snowflake_ids, "ebnf"), inline=False)
                    .set_footer(
                        text=f"on_command_error: {cmd_name}",
                        icon_url=ctx.guild.icon if ctx.guild else ctx.author.display_avatar,
                    )
                )
                await ctx.bot.exc_manager.register_error(error, metadata_embed, ctx.channel.id)
                if ctx.channel.id == ctx.bot.hideout.spam_channel_id:
                    # we don't need any extra embeds;
                    return

        response_embed = helpers.error_handler_response_embed(error, desc, unexpected=is_unexpected)
        await ctx.reply(embed=response_embed, ephemeral=True)

    # todo: I don't think it's a proper way of doing this;
    async def get_or_fetch_app_emojis(self, *, force: bool = False) -> list[discord.Emoji]:
        """Get application emojis and cache them."""
        self.app_emojis = []
        if not self.app_emojis or force:
            self.app_emojis = await self.fetch_application_emojis()

        return self.app_emojis
