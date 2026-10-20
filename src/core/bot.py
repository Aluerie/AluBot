"""Bot.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime as dt
import logging
import sys
from typing import TYPE_CHECKING, Any, Literal, override

import discord
from discord.ext import commands

from config import env
from ext import DISABLED_EXTENSIONS, EXT_PACKAGE
from shared import clock, fmt  # TODO: fix it
from shared.concepts import BotBase
from utils import MISSING, const, disambiguator, errors, transposer

from .bases import AluContext
from .timer_manager import TimerManager
from .tree import AluAppCommandTree

if TYPE_CHECKING:
    import asyncpg
    from aiohttp import ClientSession

    from shared.concepts.db import PoolTypedWithAny


__all__ = ("AluBot",)

log = logging.getLogger(__name__)


class AluBot(BotBase, commands.Bot):
    """AluBot.

    Extended subclass over discord.py's `commands.Bot`
    * Used to interact with the Discord WebSocket, API and more.
    * Includes discord.py's `ext.commands` extension to organize cogs/commands framework.
    """

    if TYPE_CHECKING:
        command_prefix: set[Literal["~", "$"]]  # ty: ignore[invalid-mutable-override]
        listener_connection: asyncpg.Connection[asyncpg.Record]
        logs_via_webhook_handler: Any
        tree: AluAppCommandTree
        user: discord.ClientUser

    def __init__(
        self,
        *,
        session: ClientSession,
        pool: PoolTypedWithAny,
        is_subset_mode: bool,
        is_test_account: bool,
    ) -> None:
        """Initialize the AluBot.

        Parameters
        ----------
        session
            aiohttp.ClientSession to use within the bot.
        pool
            A connection pool to the database.
        is_subset_mode
            A boolean flag indicating whether we launch the whole bot (e.g. production)
            or just a subset of features (e.g. testing environment).
        is_test_account
            whether the bot is a testing version (YenBot) or main production bot (AluBot).
            I just like to use different discord bot token to debug issues, test new code, etc.
        """
        if is_test_account:
            # test account
            self.test = True
            self.prefix = "~"
            ping_role_mention = env.PING_TEST_MENTION
        else:
            # production account
            self.test = False
            self.prefix = "$"
            ping_role_mention = env.PING_PROD_MENTION

        super(commands.Bot, self).__init__(
            command_prefix={self.prefix},
            activity=discord.Streaming(name="\N{HEAVY BLACK HEART}", url="https://twitch.tv/irene_adler__"),
            intents=discord.Intents(
                dm_messages=True,
                emojis_and_stickers=True,
                guild_messages=True,
                guilds=True,
                members=True,
                message_content=True,
                moderation=True,
                presences=True,
                voice_states=True,
            ),
            allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False),
            tree_cls=AluAppCommandTree,
            strip_after_prefix=True,
            case_insensitive=True,
            help_command=None,
            # allowed_contexts=discord.app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
            # allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=True),
        )
        super().__init__(
            session,
            ping_role_mention=ping_role_mention,
            error_webhook_url=env.WEBHOOK_ERROR,
            notification_webhook_url=env.WEBHOOK_NOTIFICATION,
        )

        self.pool: PoolTypedWithAny = pool
        self.session: ClientSession = session
        self.extensions_to_load: tuple[str, ...] = self.get_extensions(
            is_subset_mode=is_subset_mode, package=EXT_PACKAGE, disabled_extensions=DISABLED_EXTENSIONS
        )

        # Stats / Info
        self.repository_url: str = "https://github.com/Aluerie/AluBot"
        self.bot_app_info: discord.AppInfo
        self.ready_flag: bool = False
        self.launch_time: dt.datetime = clock.utcnow()

        # idk
        self.transposer: transposer.TransposeClient = transposer.TransposeClient(session=session)
        self.disambiguator: disambiguator.Disambiguator = disambiguator.Disambiguator()
        self.app_emojis: list[discord.Emoji] = []
        self.launch_time: dt.datetime = MISSING

    @discord.utils.cached_property
    def invite_link(self) -> str:
        """Get invite link for the bot.

        Note for developers
        -------------------
        Please, make sure `permissions` are the same as the ones checked in this page (Guild Install):
        https://discord.com/developers/applications/713124699663499274/installation
        """
        return discord.utils.oauth_url(
            client_id=self.user.id,
            permissions=discord.Permissions(
                add_reactions=True,
                attach_files=True,
                connect=True,
                embed_links=True,
                manage_messages=True,
                manage_roles=True,
                manage_webhooks=True,
                read_message_history=True,
                send_messages=True,
                send_messages_in_threads=True,
                speak=True,
                use_external_emojis=True,
                view_audit_log=True,
                view_channel=True,
            ),
            scopes=(
                "bot",
                "applications.commands",
            ),
        )

    @override
    async def on_error(self: AluBot, event: str, *args: Any, **kwargs: Any) -> None:
        """Event error: called when an exception is raised in an event listener.

        Parameters
        ----------
        event
            The name of the event that raised the exception.
        args
            The positional arguments for the event that raised the exception.
        kwargs
            The keyword arguments for the event that raised the exception.
        """
        (_exception_type, exception, _traceback) = sys.exc_info()
        assert exception is not None, "Somehow `on_error` fired with exception being `None`."
        if isinstance(exception, commands.CommandInvokeError):
            # Silence command errors that somehow get bubbled up far enough here
            return

        embed = discord.Embed(
            color=0xA32952,
            title=f"Event Error: `{event}`",
            description=f"Event Args:\n{fmt.pformat_args(*args)}",
        ).set_footer(text=f"{self.__class__.__name__}.on_error: {event}")
        await self.error_notification_manager.register(exception, embed)

    @override
    async def on_command_error(
        self,
        ctx: AluContext,
        error: commands.CommandError | Exception,
    ) -> None:  # ty: ignore[invalid-method-override]
        """Command error: called when an error is raised while invoking a ctx command."""
        if ctx.is_error_handled is True:
            return

        if isinstance(error, commands.CommandInvokeError):
            # we aren't interested in the chain traceback.
            error = error.original

        match error:
            case _:
                embed = discord.Embed(
                    color=0x890620,
                    title=f"Ctx Command Error: `{ctx.clean_prefix}{ctx.command}`",
                )
                await ctx.bot.error_notification_manager.register(error, embed)

    async def on_command_error_old(
        self,
        ctx: AluContext,
        error: commands.CommandError | Exception,
    ) -> None:
        """Command error: called when an error is raised while invoking a ctx command."""
        if ctx.is_error_handled is True:
            return

        # error handler working variables
        desc = "No description"
        is_unexpected = False

        # error handler itself.

        if isinstance(error, commands.CommandInvokeError):
            # we aren't interested in the chain traceback.
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
                desc = (
                    f"Please retry in `{clock.human_timedelta(seconds=error.retry_after, mode='short')} {clock.discord()}`"
                )
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
                    "\n".join(f"[{name}]: {value!r}" for name, value in ctx.kwargs.items()) if ctx.kwargs else "No arguments"
                )
                snowflake_ids = (
                    f"author  = {ctx.author.id}\n"
                    f"channel = {ctx.channel.id}\n"
                    f"guild   = {ctx.guild.id if ctx.guild else 'DM Channel'}"
                )
                metadata_embed = (
                    discord
                    .Embed(
                        title=f"Ctx Command Error: `{ctx.clean_prefix}{ctx.command}`",
                        url=ctx.message.jump_url,
                        description=textwrap.shorten(ctx.message.content, width=1024),
                    )
                    .set_author(
                        name=f"@{ctx.author} in #{ctx.channel} ({ctx.guild.name if ctx.guild else 'DM Channel'})",
                        icon_url=ctx.author.display_avatar,
                    )
                    .add_field(name="Command Args", value=shared_fmt.codeblock(kwargs_join, "ps"), inline=False)
                    .add_field(name="Snowflake IDs", value=shared_fmt.codeblock(snowflake_ids, "ebnf"), inline=False)
                    .set_footer(
                        text=f"on_command_error: {cmd_name}",
                        icon_url=ctx.guild.icon if ctx.guild else ctx.author.display_avatar,
                    )
                )
                await ctx.bot.error_notification_manager.register(error, metadata_embed)

        response_embed = helpers.error_handler_response_embed(error, desc, unexpected=is_unexpected)
        await ctx.reply(embed=response_embed, ephemeral=True)

    async def on_ready(self) -> None:
        """Handle `ready` event."""
        if not self.ready_flag:
            self.launch_time = clock.utcnow()
            self.ready_flag = True
        log.info("Logged in as `%s`", self.user)

    @override
    async def setup_hook(self) -> None:
        self.bot_app_info = await self.application_info()

        failed_to_load_extensions = False
        for ext in self.extensions_to_load:
            try:
                await self.load_extension(ext)
            except commands.ExtensionError as error:
                failed_to_load_extensions = True
                embed = discord.Embed(
                    color=0xDA9F93,
                    description=f"Failed to load extension `{ext}`.",
                ).set_footer(text=f'setup_hook: loading extension "{ext}"')
                await self.error_notification_manager.register(error, embed)

        self.timers = TimerManager(bot=self)

        if self.test:
            if failed_to_load_extensions:
                log.info("Autosync: cancelled %s One or more cogs failed to load.", const.Tick.No)
            else:
                self.loop.create_task(self.try_autosync_hideout())

    async def try_autosync_hideout(self) -> None:
        """Wrap `auto_sync_hideout` into `try/except` with some logging."""
        try:
            result = await self.autosync_hideout()
        except Exception as err:
            log.exception("Autosync: failed %s.", const.Tick.No, exc_info=err)
        else:
            phrase = f"success {const.Tick.Yes}" if result else f"not needed {const.Tick.Black}"
            log.info("Autosync: %s.", phrase)

    async def autosync_hideout(self) -> bool:
        """Try automatic `copy_global_to` + `sync` Hideout Guild for easier testing purposes.

        ?tag ass (auto-syncing sucks) and all, but it's just too convenient to pass on.
        The function is using non-global sync methods so should be fine on rate-limits.

        Sources
        -------
        * DuckBot-Discord/DuckBot (MPL v2 License), `try_autosync` function
            https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/bot.py
        """
        # safeguard. Need the app id.
        await self.wait_until_ready()

        guild = discord.Object(id=self.hideout.id)
        self.tree.copy_global_to(guild=guild)

        new: list[dict[str, Any]] = [cmd.to_dict(self.tree) for cmd in self.tree.get_commands(guild=guild)]
        old: list[dict[str, Any]] = [r["payload"] for r in await self.pool.fetch("SELECT payload FROM auto_sync")]

        if len(new) == len(old) and all(p in old for p in new):
            # Compared dicts, seems same.
            return False

        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute("DELETE FROM auto_sync")
            await conn.executemany("INSERT INTO auto_sync (payload) VALUES ($1)", [(p,) for p in new])
        await self.tree.sync(guild=guild)
        return True

    async def on_ready_old(self) -> None:
        """Handle `ready` event."""
        if not hasattr(self, "launch_time"):
            self.launch_time = clock.utcnow()
        log.info("Logged in as `%s`", self.user)
        if not self.test:
            await self.send_warning("AluBot is ready.")

    @override
    async def start(self) -> None:  # ty: ignore[invalid-method-override]
        token = env.DISCORD_TOKEN_YENBOT if self.test else env.DISCORD_TOKEN_ALUBOT
        await super().start(token, reconnect=True)

    @override
    async def get_context(
        self, origin: discord.Interaction | discord.Message, /, *, cls: type[commands.Context[Any]] = AluContext
    ) -> AluContext:
        return await super().get_context(origin, cls=AluContext)

    # @override
    # async def get_context(
    #     self, origin: discord.Message | discord.Interaction[discord.Client], /, *, cls: type[AluContext] = ...
    # ) -> Any:
    #     return super().get_context(origin, cls=cls)

    @property
    def owner(self) -> discord.User:
        """Bot's owner."""
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

    def initialize_lol(self) -> None:
        """Instantiate League of Legends Client."""
        if not hasattr(self, "lol"):
            from utils.lol import LeagueClient

            self.lol = LeagueClient(self)  # pyright: ignore[reportUninitializedInstanceVariable]

    def instantiate_dota(self) -> None:
        """Instantiate Dota 2 Client.

        * Dota 2 Client, allows communicating with Dota 2 Game Coordinator and Steam
        """
        if not hasattr(self, "dota"):
            from utils.dota.steamio_client import DotaClient

            self.dota = DotaClient(self)  # pyright: ignore[reportUninitializedInstanceVariable]

    def instantiate_github(self) -> None:
        """Initialize GitHub REST API Client."""
        if not hasattr(self, "github"):
            from githubkit import GitHub

            self.github = GitHub(config["TOKENS"]["GIT_PERSONAL"])  # pyright: ignore[reportUninitializedInstanceVariable]

    async def instantiate_twitch(self) -> None:
        """Instantiate subclassed twitchio's Twitch Client."""
        if not hasattr(self, "twitch"):
            from utils.twitch import AluTwitchClient

            self.twitch = AluTwitchClient(self)  # pyright: ignore[reportUninitializedInstanceVariable]
            await self.twitch.login()

    def instantiate_tz_manager(self) -> None:
        """Instantiate TimeZone Manager."""
        if not hasattr(self, "tz_manager"):
            from utils.timezones import TimezoneManager

            self.tz_manager = TimezoneManager(self)  # pyright: ignore[reportUninitializedInstanceVariable]

    @override
    async def close(self) -> None:
        """Close the connection to Discord while cleaning up other open sessions and clients."""
        log.info("%s is closing.", self.__class__.__name__)
        if not self.test:
            await self.send_warning("AluBot is closing.")

        await self.pool.close()
        for client_attribute_name in ("twitch", "dota", "lol"):
            if hasattr(self, client_attribute_name):
                await getattr(self, client_attribute_name).close()
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

    @override
    def webhook_from_url(self, url: str) -> discord.Webhook:
        """Shortcut to discord.Webhook.from_url with some filled args.

        The override adds some specific to discord bots arguments.
        """
        return discord.Webhook.from_url(url=url, session=self.session, client=self, bot_token=self.http.token)

    async def webhook_from_database(self, channel_id: int) -> discord.Webhook:
        """Fetch webhook_url from the database by the `channel_id`."""
        query = "SELECT url FROM webhooks WHERE channel_id = $1"
        webhook_url: str | None = await self.pool.fetchval(query, channel_id)
        if webhook_url is not None:
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
        """A listener for processing commands from discord messages that the bot can see.

        Currently, the bot doesn't allow text command anywhere except my private hideout server.
        People should use slash commands. Some remaining text commands are dev-only.

        Note that this doesn't change behavior of other "on_message" listeners,
        i.e. they will still listen to messages from all guilds.
        """
        if message.guild and message.guild.id == const.Guild.hideout and not message.author.bot:
            # only process commands in my own private server and only from me (the only non-bot account in there);
            await self.process_commands(message)

    # TODO: I don't think it's a proper way of doing this;
    async def get_or_fetch_app_emojis(self, *, force_fetch: bool = False) -> list[discord.Emoji]:
        """Get application emojis and cache them."""
        if not self.app_emojis or force_fetch:
            self.app_emojis = await self.fetch_application_emojis()

        return self.app_emojis
