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

import ext
from config import env
from shared import clock, errors, fmt
from shared.concepts import BotBase
from utils import const

from .interactions import AppCommandTree
from .scheduler import Scheduler

if TYPE_CHECKING:
    import datetime as dt

    import asyncpg
    from aiohttp import ClientSession
    from PIL import Image

    from shared.concepts.db import PoolTypedWithAny


__all__ = (
    "Bot",
    "Context",
)

log = logging.getLogger(__name__)

type Context = commands.Context[Bot]


class Bot(BotBase, commands.Bot):
    """AluBot.

    Extended subclass over discord.py's `commands.Bot`
    * Used to interact with the Discord WebSocket, API and more.
    * Includes discord.py's `ext.commands` extension to organize cogs/commands framework.
    """

    if TYPE_CHECKING:
        command_prefix: set[Literal["~", "$"]]  # ty: ignore[invalid-mutable-override]
        listener_connection: asyncpg.Connection[asyncpg.Record]
        logs_via_webhook_handler: Any
        tree: AppCommandTree
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
            tree_cls=AppCommandTree,
            strip_after_prefix=True,
            case_insensitive=True,
            # help_command=None,
        )
        super().__init__(
            session,
            dev_ping=ping_role_mention,
            error_webhook_url=env.WEBHOOK_ERROR,
            spam_webhook_url=env.WEBHOOK_SPAM,
        )

        self.pool: PoolTypedWithAny = pool
        self.session: ClientSession = session
        self.extensions_to_load: tuple[str, ...] = self.get_extensions(is_subset_mode=is_subset_mode)
        if not self.test:
            self.extensions_to_load += ("jishaku",)
        log.info("The list of modules (%s total) to load: %s", len(self.extensions_to_load), self.extensions_to_load)

        # Stats / Info
        self.repository_url: str = "https://github.com/Aluerie/AluBot"
        self.bot_app_info: discord.AppInfo
        self.ready_flag: bool = False
        self.launch_time: dt.datetime = clock.utcnow()

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
    async def on_error(self, event: str, /, *args: Any, **kwargs: Any) -> None:
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
        )
        if args:
            fmt.add_args_field(embed, "Event Args", *args)
        if kwargs:
            fmt.add_mapping_field(embed, "Event Kwargs", kwargs)
        if isinstance(exception, errors.BotError) and exception.data:
            fmt.add_mapping_field(embed, "BotError Data", exception.data)
        await self.error_notification_manager.register(exception, embed)

    @override
    async def on_command_error(
        self,
        ctx: Context,
        error: commands.CommandError,
    ) -> None:
        """Command error: called when an error is raised while invoking a ctx command."""
        # if ctx.is_error_handled is True:W
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
                if not await self.respond_per_policy(error, respond=ctx.reply):
                    return

                embed = (
                    discord
                    .Embed(
                        color=0x890620,
                        title=f"Ctx Command Error: `{ctx.clean_prefix}{ctx.command}`",
                        url=ctx.message.jump_url,
                        description=fmt.shorten(ctx.message.content, limit=1024),
                        timestamp=ctx.message.created_at,
                    )
                    .set_author(
                        name=f"@{ctx.author} in #{ctx.channel}",
                        icon_url=ctx.author.display_avatar,
                    )
                    .set_footer(
                        text=ctx.guild.name if ctx.guild else "DM Channel",
                        icon_url=ctx.guild.icon if ctx.guild else ctx.author.display_avatar,
                    )
                )
                fmt.add_args_field(embed, "Ctx Args", *ctx.args[2:])  # cut `self, ctx: Context`
                fmt.add_mapping_field(embed, "Ctx Kwargs", ctx.kwargs)
                fmt.add_mapping_field(
                    embed,
                    "Snowflake IDs",
                    {
                        "author": ctx.author.id,
                        "channel": ctx.channel.id,
                        "guild": ctx.guild.id if ctx.guild else None,
                        "message": ctx.message.id,
                    },
                )
                if isinstance(error, errors.BotError) and error.data:
                    fmt.add_mapping_field(embed, "BotError Data", error.data)
                await ctx.bot.error_notification_manager.register(error, embed)

    #########################################################################################################################
    # STARTING THE BOT
    #########################################################################################################################

    @override
    def get_extensions(self, *, is_subset_mode: bool) -> tuple[str, ...]:  # ty: ignore[invalid-method-override]
        """Get list of bot extensions to load."""
        return super().get_extensions(is_subset_mode=is_subset_mode, package=ext)

    @override
    async def setup_hook(self) -> None:
        self.bot_app_info = await self.application_info()
        await const.load_emojis(self)

        failed_to_load_extensions = False
        for extension in self.extensions_to_load:
            try:
                await self.load_extension(extension)
            except commands.ExtensionError as error:
                failed_to_load_extensions = True
                embed = discord.Embed(
                    color=0xDA9F93,
                    description=f"Failed to load extension `{extension}`.",
                ).set_footer(text=f'setup_hook: loading extension "{extension}"')
                await self.error_notification_manager.register(error, embed)

        self.timers = Scheduler(bot=self)

        if self.test:
            if failed_to_load_extensions:
                log.info("Autosync: cancelled ❌ One or more cogs failed to load.")
            else:
                self.loop.create_task(self.try_autosync_hideout())

    async def try_autosync_hideout(self) -> None:
        """Wrap `auto_sync_hideout` into `try/except` with some logging."""
        try:
            result = await self.autosync_hideout()
        except Exception as err:
            log.exception("Autosync: failed ❌", exc_info=err)
        else:
            phrase = "success ✅" if result else "not needed 🫰"
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

        guild = discord.Object(id=const.Guild.hideout)
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

    #########################################################################################################################
    # TYPE FRIENDLY LOOKUPS (Kinda unnecessary but hey)
    #########################################################################################################################

    def get_text_channel(self, channel_id: int) -> discord.TextChannel:
        """Return the cached text channel with the given ID.

        Parameters
        ----------
        channel_id
            The ID of the channel to look up.

        Returns
        -------
        discord.TextChannel
            The matching text channel.

        Raises
        ------
        LookupError
            If no channel with this ID is in the bot's cache.
        TypeError
            If the channel exists but is not a ``discord.TextChannel``.
        """
        channel = self.get_channel(channel_id)
        if channel is None:
            msg = f"Channel {channel_id} not found in cache"
            raise LookupError(msg)
        if not isinstance(channel, discord.TextChannel):
            msg = f"Channel {channel_id} is {type(channel).__name__}, expected TextChannel"
            raise TypeError(msg)
        return channel

    def get_role(self, guild_id: int, role_id: int) -> discord.Role:
        """Return the cached role with the given ID.

        Parameters
        ----------
        guild_id
            The ID of the guild containing the role.
        role_id
            The ID of the role to look up.

        Returns
        -------
        discord.Role
            The matching role.

        Raises
        ------
        LookupError
            If the guild or role is not in the bot's cache.
        """
        guild = self.get_guild(guild_id)
        role = guild.get_role(role_id) if guild else None
        if role is None:
            msg = f"Role {role_id} not found in guild {guild_id}"
            raise LookupError(msg)
        return role

    # @staticmethod
    # def get_guild_role(guild: discord.Guild, role_id: int) -> discord.Role:
    #     """Return the role with the given ID from the guild.

    #     Parameters
    #     ----------
    #     guild
    #         The guild to search.
    #     role_id
    #         The ID of the role to look up.

    #     Returns
    #     -------
    #     The matching role.

    #     Raises
    #     ------
    #     LookupError
    #         If the role is not in the guild.
    #     """
    #     role = guild.get_role(role_id)
    #     if role is None:
    #         msg = f"Role {role_id} not found in guild {guild.id}"
    #         raise LookupError(msg)
    #     return role

    #########################################################################################################################
    # TRANSPOSE X TO Y (Mainly to transpose to/from ``discord.File``, but some other types too)
    #########################################################################################################################

    @staticmethod
    def str_to_file(string: str, filename: str = "file.txt") -> discord.File:
        """Convert ``str`` to ``discord.File``."""
        fp = io.BytesIO(io.StringIO(string).read().encode("utf8"))
        fp.seek(0)
        return discord.File(fp, filename=filename)

    @staticmethod
    def image_to_file(image: Image.Image, filename: str = "fromAluBot.png", fmt: str = "PNG") -> discord.File:
        """Convert ``PIL.Image.Image`` to ``discord.File``."""
        image_binary = io.BytesIO()
        image.save(image_binary, fmt)
        image_binary.seek(0)
        return discord.File(fp=image_binary, filename=filename)
