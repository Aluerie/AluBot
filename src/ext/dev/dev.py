# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Developer."""

from __future__ import annotations

import asyncio
import unicodedata
from typing import TYPE_CHECKING, Any, ClassVar, Literal, assert_never, cast, override

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from loguru import logger

from config import env
from core import DevCog
from shared import errors, fmt, systemd
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from core import Bot, Context, Interaction


type SyncSpecLiteral = Literal["global", "current", "copy", "clear", "~", "*", "^"]
type SlashSyncSpecLiteral = Literal["global", "current", "copy", "clear"]


class Dev(DevCog):
    """Developer tools for keeping Discord's command registry in sync with the bot.

    Features
    --------
    * `sync` prefix command and `/sync-dev` slash command for syncing the app command tree;
    * `autosync` task that syncs global and Hideout commands shortly once the bot is ready (skipped on the test bot);
    * `healthcheck` task that pings healthchecks.io while the bot is healthy (only in prod on the VPS).
    """

    @override
    async def cog_load(self) -> None:
        if not self.bot.test:
            self.autosync.start()
        # only the VPS (a systemd service) pings, so a bot running at home doesn't keep the check green
        if not self.bot.test and env.HEALTHCHECK_URL and systemd.is_systemd_service():
            self.healthcheck.add_exception_type(aiohttp.ClientError, TimeoutError)
            self.healthcheck.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.autosync.cancel()
        self.healthcheck.cancel()
        await super().cog_unload()

    # --- HEALTHCHECK --------------------------------------------------------------------------------------------------

    @loop(minutes=5, wait_for_ready=True)
    async def healthcheck(self) -> None:
        """Ping the healthchecks.io check while the bot is connected to Discord and its database answers.

        healthchecks.io alerts me when these pings stop coming.
        """
        # `is_ready()` stays True while discord.py reconnects, so require a live gateway connection
        if not self.bot.ws.open:
            return
        try:
            await self.bot.pool.fetchval("SELECT 1")
        except Exception as exc:  # ruff: ignore[blind-except] any database failure just means "not healthy"
            logger.warning("Healthcheck: skipping the ping, the database doesn't answer: {!r}", exc)
            return
        async with self.bot.session.get(env.HEALTHCHECK_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()

    # --- AUTOSYNC -----------------------------------------------------------------------------------------------------

    @loop(count=1, wait_for_ready=True)
    async def autosync(self) -> None:
        """Sync global and Hideout guild commands once after startup.

        Convenient enough to keep over the manual `?tag ass` workflow. If we ever get rate limited,
        replace it with something smarter (e.g. sync only on changes or more sleep time).

        Notes
        -----
        * Not related to `AluBot.autosync_hideout`, which must stay on the bot class:
          it runs on every test-bot launch, while this cog is not always loaded.
        """
        # Global
        await self.bot.tree.sync()
        # Hideout Guild
        await asyncio.sleep(30.0)
        await self.bot.tree.sync(guild=discord.Object(id=const.Guild.hideout))

        logger.success("Synced global and Hideout bound commands.")

    # --- SYNC COMMANDS ------------------------------------------------------------------------------------------------

    async def sync_command_worker(
        self,
        spec: SyncSpecLiteral | None,
        current_guild: discord.Guild | None,
        guilds: list[discord.Object],
    ) -> str:
        """Sync the app command tree according to the given arguments.

        Shared implementation of the prefix and slash sync commands.

        Parameters
        ----------
        spec
            How to sync:

            * `None` and `"global"` sync globally;
            * `"current"`/`"~"`, `"copy"`/`"*"` and `"clear"`/`"^"` act on `current_guild`.

            Must be `None` when `guilds` is given.
        current_guild
            Guild where the command was invoked, `None` outside of a guild (e.g. DMs).
        guilds
            Explicit guilds to sync (prefix command only). Failures are collected per guild instead of aborting
            the whole batch.

        Returns
        -------
        str
            Human-readable summary of what was synced.

        References
        ----------
        Umbra's sync command, which this follows:
        https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
        (also available as `?tag usc` in the discord.py server).
        """
        # Multiple Guilds sync
        if guilds:
            if spec is not None:
                msg = "`spec` can't be combined with explicit guild IDs."
                raise errors.RespondWithError(msg)
            ok = 0
            failed: list[int] = []
            for guild in guilds:
                try:
                    await self.bot.tree.sync(guild=guild)
                except discord.HTTPException as e:
                    logger.warning("Failed to sync guild {}: {}", guild.id, e)
                    failed.append(guild.id)
                else:
                    ok += 1
            msg = f"Synced the tree to {ok}/{len(guilds)} guilds."
            if failed:
                msg += f" Failed: {', '.join(map(str, failed))}."
            return msg

        # Global sync
        if spec in {None, "global"}:
            synced = await self.bot.tree.sync()
            return f"Synced {len(synced)} commands globally."

        # Spec sync
        if current_guild is None:
            msg = f"`{spec}` can only be used inside a guild."
            raise errors.RespondWithError(msg)

        match spec:
            case "current" | "~":
                synced = await self.bot.tree.sync(guild=current_guild)
            case "copy" | "*":
                self.bot.tree.copy_global_to(guild=current_guild)
                synced = await self.bot.tree.sync(guild=current_guild)
            case "clear" | "^":
                self.bot.tree.clear_commands(guild=current_guild)
                await self.bot.tree.sync(guild=current_guild)
                return "Cleared all commands from the current guild."
            case _:  # Unreachable via commands.
                assert_never(spec)
        return f"Synced {len(synced)} commands to the current guild."

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command(name="sync-dev")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.choices(
        spec=[
            app_commands.Choice(name="🌐 Global Sync", value="global"),
            app_commands.Choice(name="🏠 Current Guild", value="current"),
            app_commands.Choice(name="🥷 Copy Global commands to Current Guild", value="copy"),
            app_commands.Choice(name="🧹 Clear Current Guild", value="clear"),
        ],
    )
    async def slash_sync_dev(self, interaction: Interaction, spec: SlashSyncSpecLiteral = "global") -> None:
        """📡 Sync bot's app tree.

        Parameters
        ----------
        spec
            Method to sync the bot's commands with.
        """
        await interaction.response.defer()
        content = await self.sync_command_worker(spec, current_guild=interaction.guild, guilds=[])
        await interaction.followup.send(content)

    @commands.command(name="sync", hidden=True)
    async def prefix_sync(
        self,
        ctx: Context,
        guilds: commands.Greedy[discord.Object],
        spec: SyncSpecLiteral | None = None,
    ) -> None:
        """📡 Sync bot's app tree.

        Parameters
        ----------
        guilds
            Guild IDs to sync. Cannot be combined with `spec`.
        spec
            Sync method, see examples. Defaults to a global sync.

        Examples
        --------
        | Command             | Alias     | Effect                                                      |
        | ------------------- | --------- | ----------------------------------------------------------- |
        | `$sync [global]`    |           | Send all global commands to Discord.                        |
        | `$sync current`     | `$sync ~` | Sync guild commands of the current guild.                   |
        | `$sync copy`        | `$sync *` | Copy global commands to the current guild, then sync it.    |
        | `$sync clear`       | `$sync ^` | Remove all guild-bound commands of the current guild.       |
        | `$sync 123 456 789` |           | Sync only the listed guilds and their guild-bound commands. |
        """
        content = await self.sync_command_worker(spec, current_guild=ctx.guild, guilds=guilds)
        await ctx.reply(content)

    # --- LOAD / RELOAD / UNLOAD EXTENSION COMMANDS --------------------------------------------------------------------

    ext_group = app_commands.Group(
        name="ext-dev",
        description="Load/reload/unload bot's extensions.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @staticmethod
    async def _run(interaction: Interaction, action: Callable[[str], Awaitable[None]], extension: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            await action(extension)
        except commands.ExtensionError as e:
            await interaction.followup.send(f"❌ `{extension}`: {e}")
        else:
            await interaction.followup.send(f"✅ `{extension}`")

    @ext_group.command()
    async def load(self, interaction: Interaction, extension: str) -> None:
        """🚀 Load an extension.

        Parameters
        ----------
        extension
            Extension to load.
        """
        await self._run(interaction, self.bot.load_extension, extension)

    @ext_group.command()
    async def reload(self, interaction: Interaction, extension: str) -> None:
        """🔄 Reload a loaded extension.

        Parameters
        ----------
        extension
            Extension to reload.
        """
        await self._run(interaction, self.bot.reload_extension, extension)

    @ext_group.command()
    async def unload(self, interaction: Interaction, extension: str) -> None:
        """🛬 Unload a loaded extension.

        Parameters
        ----------
        extension
            Extension to unload.
        """
        await self._run(interaction, self.bot.unload_extension, extension)

    @reload.autocomplete("extension")
    @unload.autocomplete("extension")
    async def loaded_autocomplete(self, _: Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Suggest currently loaded extensions."""
        return [
            app_commands.Choice(name=ext, value=ext) for ext in self.bot.extensions if current.lower() in ext.lower()
        ][:25]

    @load.autocomplete("extension")
    async def unloaded_autocomplete(self, _: Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Suggest available but not yet loaded extensions."""
        available = self.bot.get_extensions(is_subset_mode=False)
        return [
            app_commands.Choice(name=name, value=name)
            for name in available
            if name not in self.bot.extensions and current.lower() in name.lower()
        ][:25]

    # --- DEV COMMANDS -------------------------------------------------------------------------------------------------
    # These commands aren't public only because I don't think people would find them useful.
    # It's just some helping commands that I use myself when coding the bot.

    @commands.command(name="invite-link")
    async def invite_link(self, ctx: Context) -> None:
        """Get invite link for the bot.

        Somewhat pointless since 'Add App' button exists.
        But it's useful to have for @YenBot where I removed that button.
        """
        await ctx.send(self.bot.invite_link)

    tools_group = app_commands.Group(
        name="tools-dev",
        description="Useful developer tools.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    # fmt: off
    KNOWN_CHAR_ABBREVIATIONS: ClassVar[dict[str, str]] = {
        "\u0000": "NUL", "\u0009": "TAB", "\u000a": "LF", "\u000d": "CR", "\u00a0": "NBSP", "\u00ad": "SHY",
        "\u200b": "ZWSP", "\u200c": "ZWNJ", "\u200d": "ZWJ", "\u200e": "LRM", "\u200f": "RLM", "\u202a": "LRE",
        "\u202b": "RLE", "\u202c": "PDF", "\u202d": "LRO", "\u202e": "RLO", "\u2060": "WJ", "\u2066": "LRI",
        "\u2067": "RLI", "\u2068": "FSI", "\u2069": "PDI", "\ufe0e": "VS15", "\ufe0f": "VS16", "\ufeff": "BOM",
    }
    # fmt: on

    def char_info_worker(self, char: str) -> tuple[str, str]:
        r"""Return the Python escape for a character and some info.

        Example
        -------
        "🦢" -> ("\N{SWAN}", "[`\U0001f9a2`](<fileformat link>): SWAN — 🦢")
        """
        codepoint = ord(char)
        alias = self.KNOWN_CHAR_ABBREVIATIONS.get(char)
        name = unicodedata.name(char, "")
        if alias is not None:
            full_name = f"{name} ({alias})" if name else alias
            escape = f"\\N{{{alias}}}"
        elif name:
            full_name = name
            escape = f"\\N{{{name}}}"
        else:
            full_name = "(No name found)"
            escape = f"\\U{codepoint:08x}"

        markdown_link = f"[`\\U{codepoint:08x}`](https://www.fileformat.info/info/unicode/char/{codepoint:x})"
        text_view = discord.utils.escape_markdown(char)
        return escape, f"{markdown_link}: {full_name} \N{EM DASH} {text_view}"

    @tools_group.command()
    async def charinfo(self, interaction: Interaction, characters: app_commands.Range[str, 1, 10]) -> None:
        """🔤 Show Unicode information about character(-s).

        Only up to 10 characters (Unicode code points) at a time though.

        Parameters
        ----------
        characters
            Input up to 10 characters to get format info about.
        """
        escapes, lines = zip(*(self.char_info_worker(c) for c in characters), strict=True)
        echo = discord.utils.escape_markdown(characters)
        codeblock = fmt.codeblock("\n".join(f"'{e}'" for e in escapes))
        bullet_list = "\n".join(f"* {line}" for line in lines)
        await interaction.response.send_message(
            content=f"{echo}\n{codeblock}\n{bullet_list}",
            allowed_mentions=discord.AllowedMentions.none(),
            suppress_embeds=True,
        )

    @commands.command(name="py")
    async def py(self, ctx: Context, *, code: str) -> None:
        """Evaluate Python code via jishaku.

        Alias for `jsk py`.

        Parameters
        ----------
        code
            The code to run. Can be wrapped in a codeblock.
        """
        jsk_py = cast("commands.Command[Any, ..., Any] | None", self.bot.get_command("jsk py"))
        if jsk_py is None:
            await ctx.reply("It seems, jishaku is not loaded")
            return
        await ctx.invoke(jsk_py, argument=codeblock_converter(code))


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Dev(bot))
