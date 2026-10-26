"""Developer.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, assert_never, cast, override

import discord
from discord import app_commands
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

from core import DevCog
from shared import errors, fmt
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from core import Bot, Context, Interaction


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


type SyncSpecLiteral = Literal["global", "current", "copy", "clear", "~", "*", "^"]
type SlashSyncSpecLiteral = Literal["global", "current", "copy", "clear"]


class Dev(DevCog):
    """Developer tools for keeping Discord's command registry in sync with the bot.

    Features
    --------
    * `sync` prefix command and `/sync-dev` slash command for syncing the app command tree;
    * `autosync` task that syncs global and Hideout commands shortly once the bot is ready (skipped on the test bot).
    """

    DATABASE_CHANNEL_ID: Final[int] = 1541985585810378823

    @override
    async def cog_load(self) -> None:
        if not self.bot.test:
            self.autosync.start()
        self.database_backup.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.database_backup.stop()
        self.autosync.cancel()
        await super().cog_unload()

    @override
    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)  # ty: ignore[invalid-argument-type]

    @override
    async def interaction_check(self, interaction: Interaction) -> bool:
        return await self.bot.is_owner(interaction.user)  # ty: ignore[invalid-argument-type]

    ####################################################################################################################
    # AUTOSYNC
    ####################################################################################################################

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

        log.info("Synced global and Hideout bound commands.")

    ####################################################################################################################
    # SYNC COMMANDS
    ####################################################################################################################

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
                    log.warning("Failed to sync guild %s: %s", guild.id, e)
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

    ####################################################################################################################
    # LOAD / RELOAD / UNLOAD EXTENSION COMMANDS
    ####################################################################################################################

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

    ####################################################################################################################
    # DATABASE BACKUP
    ####################################################################################################################

    def get_database_channel(self) -> discord.TextChannel:
        """Get the text channel used for database backups."""
        return self.bot.get_text_channel(self.DATABASE_CHANNEL_ID)

    @loop(time=dt.time(hour=18, minute=5, tzinfo=dt.UTC))
    async def database_backup(self) -> None:
        """Daily task to backup the bot's database.

        Sends pg_dump to my private discord server.
        """
        if self.bot.test:
            return

        path = Path(".temp/alubot.sql")
        path.parent.mkdir(exist_ok=True)

        try:
            proc = await asyncio.create_subprocess_exec(
                "pg_dump",
                "-f",
                str(path),
                "alubot",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                raise
            if proc.returncode != 0:
                msg = f"pg_dump exited with {proc.returncode}: {stderr.decode()}"
                raise RuntimeError(msg)
            await self.get_database_channel().send(file=discord.File(path, filename=path.name))
        finally:
            path.unlink(missing_ok=True)

    ####################################################################################################################
    # PROJECT CONTROL
    ####################################################################################################################

    project_group = app_commands.Group(
        name="project-dev",
        description="Control Irene's projects",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    PROJECTS: ClassVar[dict[str, str]] = {
        "irebot": "../IrenesBot/.temp/irebot.log",
        "alubot": ".temp/alubot.log",
        "dota2bot": "../Dota2Bot/.temp/d2b.log",
    }

    @project_group.command(name="logs")
    @app_commands.choices(project=[app_commands.Choice(name=p, value=log_path) for p, log_path in PROJECTS.items()])
    async def project_logs(self, interaction: Interaction, project: str) -> None:
        """🪵 Get project's logs."""
        await interaction.response.defer()
        await interaction.followup.send(file=discord.File(project))

    @project_group.command(name="restart")
    @app_commands.choices(project=[app_commands.Choice(name=p, value=p) for p in PROJECTS])
    async def project_restart(self, interaction: Interaction, project: str) -> None:
        """🔌 Restart project's process.

        Usable to restart the bot (or other projects) without logging to VPS machine or committing something.
        Sometimes, it's just more comfortable to do it from discord window or mobile.

        Parameters
        ----------
        project
            Project to restart.
        """
        await interaction.response.send_message("Rebooting in 3 2 1")
        await asyncio.sleep(3)
        proc = await asyncio.create_subprocess_exec(
            "sudo",
            "systemctl",
            "restart",
            project,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            log.error("Failed to restart %s: %s", project, stderr.decode())
            await interaction.followup.send(f"Something went wrong:\n{fmt.codeblock(stderr.decode()[:1500])}")

    @project_group.command(name="journal")
    @app_commands.choices(project=[app_commands.Choice(name=p, value=p) for p in PROJECTS])
    async def project_journal(self, interaction: Interaction, project: str) -> None:
        """📓 Get project's journal.

        Parameters
        ----------
        project
            Project to get journal for.
        """
        await interaction.response.defer()
        proc = await asyncio.create_subprocess_exec(
            "sudo",
            "journalctl",
            f"--unit={project}",
            "-n",
            "5000",
            "--no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()
        await interaction.followup.send(file=self.bot.str_to_file(stdout.decode(), f"{project}-journal.log"))

    ####################################################################################################################
    # DEV COMMANDS
    # -------------
    # These commands aren't public only because I don't think people would find them useful.
    # It's just some helping commands that I use myself when coding the bot.
    ####################################################################################################################

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
