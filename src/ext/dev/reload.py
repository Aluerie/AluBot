"""Reload and sync related features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Literal, override

import discord
from discord import app_commands
from discord.ext import commands

from core import DevCog
from shared import errors
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from core import AluBot, Context, Interaction


__all__ = ("ReloadCog",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

type SyncSpecLiteral = Literal["global", "current", "copy", "clear", "~", "*", "^"]
type SlashSyncSpecLiteral = Literal["global", "current", "copy", "clear"]


class ReloadCog(DevCog):
    """Developer tools for keeping Discord's command registry in sync with the bot.

    Features
    --------
    * `sync` prefix command and `/sync-dev` slash command for syncing the app command tree;
    * `autosync` task that syncs global and Hideout commands shortly once the bot is ready (skipped on the test bot).
    """

    ####################################################################################################################
    # AUTOSYNC
    ####################################################################################################################

    @override
    async def cog_load(self) -> None:
        if not self.bot.test:
            self.autosync.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.autosync.cancel()
        await super().cog_unload()

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
                msg = f"Unknown sync spec: {spec!r}"
                raise errors.SomethingWentWrongError(msg, data={"spec": spec})
        return f"Synced {len(synced)} commands to the current guild."

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command(name="sync-dev")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.choices(
        spec=[
            app_commands.Choice(name="🌐 Global Sync", value="global"),
            app_commands.Choice(name="🏠 Current Guild", value="current"),
            app_commands.Choice(name="🥷 Copy Global commands to Current Guild", value="copy"),
            app_commands.Choice(name="🗑️ Clear Current Guild", value="clear"),
        ],
    )
    async def slash_sync_dev(self, interaction: Interaction, spec: SlashSyncSpecLiteral = "global") -> None:
        """🩶 Sync bot's app tree.

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
        """🩶 Sync bot's app tree.

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


async def setup(bot: AluBot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(ReloadCog(bot))
