"""Bot.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import io
import logging
import sys
from typing import TYPE_CHECKING, Any, Literal, override

import discord
from discord.ext import commands

from config import env
from ext import DISABLED_EXTENSIONS, EXT_PACKAGE
from shared import clock, fmt
from shared.concepts import BotBase
from utils import MISSING, const, disambiguator

from .bases import AluContext
from .timer_manager import TimerManager
from .tree import AluAppCommandTree

if TYPE_CHECKING:
    import datetime as dt

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
            allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=False),
            tree_cls=AluAppCommandTree,
            strip_after_prefix=True,
            case_insensitive=True,
            help_command=None,
            # allowed_contexts=discord.app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
            # allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=True),
        )
        super().__init__(
            session,
            dev_ping=ping_role_mention,
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
        # self.transposer: transposer.TransposeClient = transposer.TransposeClient(session=session)
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

    #########################################################################################################################
    # ERROR HANDLERS
    # --------------
    # Bot subclass contains error handlers for exceptions raised in event listeners and in ctx commands.
    # Note, that the files `core.tree.py`, `core.bases.views.py`, `shared.concepts.tasks` also contain error handlers:
    # app command tree errors, UI elements and tasks respectively.
    #########################################################################################################################

    @override
    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
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
        error: commands.CommandError,
    ) -> None:  # ty: ignore[invalid-method-override]
        """Command error: called when an error is raised while invoking a ctx command."""
        # if ctx.is_error_handled is True:
        #     return

        if isinstance(error, commands.CommandInvokeError | commands.HybridCommandError):
            # we aren't interested in the chain traceback.
            error: Exception = error.original

        match error:
            case commands.MissingRequiredArgument():
                await ctx.reply(f"Please, provide `{error.param.name}` argument")
            case commands.CommandNotFound():
                await ctx.reply("Command not found")
            case commands.UserInputError() | commands.CheckFailure():
                await ctx.reply(str(error))
            case _:
                if not await self._respond_per_policy(error, respond=ctx.reply):
                    return

                embed = discord.Embed(
                    color=0x890620,
                    title=f"Ctx Command Error: `{ctx.clean_prefix}{ctx.command}`",
                )
                await ctx.bot.error_notification_manager.register(error, embed)

    #########################################################################################################################
    # STARTING THE BOT
    #########################################################################################################################

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

    async def on_ready(self) -> None:
        """Handle `ready` event."""
        if not self.ready_flag:
            self.launch_time = clock.utcnow()
            self.ready_flag = True
        log.info("Logged in as `%s`", self.user)

    @override
    async def start(self) -> None:  # ty: ignore[invalid-method-override]
        token = env.DISCORD_TOKEN_YENBOT if self.test else env.DISCORD_TOKEN_ALUBOT
        await super().start(token, reconnect=True)

    #########################################################################################################################
    # MANAGEMENT
    #########################################################################################################################

    @override
    async def close(self) -> None:
        """Close the connection to Discord while cleaning up other open sessions and clients."""
        log.info("%s is closing.", self.__class__.__name__)
        await super().close()
        await self.pool.close()
        await self.session.close()

    @override
    async def get_context(
        self,
        origin: discord.Interaction | discord.Message,
        /,
        *,
        cls: type[commands.Context[Any]] = AluContext,
    ) -> AluContext:
        return await super().get_context(origin, cls=AluContext)

    @override
    async def on_message(self, message: discord.Message) -> None:
        """Listen to discord messages.

        By default, this is used for processing text commands.

        However, this bot does not support public text commands: all public users should use slash commands.

        There are a few dev-only text commands that are only allowed in my private hideout server.
        This listener makes sure of it.

        Note that this listener doesn't change behavior of other "on_message" listeners (e.g. in cogs),
        they will still listen to messages from all the guilds.
        """
        if message.guild and message.guild.id == const.Guild.hideout and not message.author.bot:
            await self.process_commands(message)

    #########################################################################################################################
    # SHORTCUTS
    #########################################################################################################################

    @property
    def owner(self) -> discord.User:
        """Bot's owner."""
        return self.bot_app_info.owner

    @override
    def webhook_from_url(self, url: str) -> discord.Webhook:
        """Shortcut to discord.Webhook.from_url with some filled args.

        The override adds some specific to discord bots arguments.
        """
        return discord.Webhook.from_url(url=url, session=self.session, client=self, bot_token=self.http.token)

    @property
    def hideout(self) -> const.HideoutGuild:
        """Shortcut for Hideout guild, its channels and roles."""
        return const.HideoutGuild(self)

    @property
    def community(self) -> const.CommunityGuild:
        """Shortcut for Community guild, its channels and roles."""
        return const.CommunityGuild(self)

    #########################################################################################################################
    # TRANSPOSE X TO Y (Mainly to transpose to/from ``discord.File``, but some other types too)
    #########################################################################################################################

    @staticmethod
    def str_to_file(string: str, filename: str = "file.txt") -> discord.File:
        """Convert ``str`` to ``discord.File``."""
        fp = io.BytesIO(io.StringIO(string).read().encode("utf8"))
        fp.seek(0)
        return discord.File(fp, filename=filename)
