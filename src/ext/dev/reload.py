"""Reload.

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

from core import AluDevCog
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from core import AluBot, AluContext, AluInteraction

__all__ = ("ReloadCog",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

type SyncSpecLiteral = Literal["global", "current", "copy", "clear", "~", "*", "^"]


# TODO: add errors.Respond when we figure out


class ReloadCog(AluDevCog):
    """Reload related features Cog.

    * Sync command (both prefix and slash);
    * Autosync task;
    """

    #########################################################################################################################
    # AUTOSYNC
    #########################################################################################################################

    @override
    async def cog_load(self) -> None:
        if not self.bot.test:
            self.autosync.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.autosync.cancel()
        await super().cog_unload()

    @loop(count=1)
    async def autosync(self) -> None:
        """Auto Syncing bot's application tree task.

        `?tag ass` and all. But It's too convenient to pass on.
        If we ever get rate limited then we will think of better measures.

        Notes
        -----
        * There is a different `autosync_hideout` task in the AluBot class. Do not move that task here because
            we want to run it on every test-bot launch while this cog is not being loaded at all times.
        """
        # Initial wait
        await asyncio.sleep(30.0)  # 1 minute
        # Global
        await self.bot.tree.sync()
        # Hideout Guild
        await asyncio.sleep(30.0)
        await self.bot.tree.sync(guild=discord.Object(id=const.Guild.hideout))

        log.info("Synced global and Hideout bound commands.")

    #########################################################################################################################
    # SYNC COMMANDS
    #########################################################################################################################

    async def sync_command_worker(
        self,
        spec: SyncSpecLiteral | None,
        current_guild: discord.Guild | None,
        guilds: list[discord.Object],
    ) -> str:
        """Worker function for both prefix and slash sync commands.

        Source
        ------
        * Umbra's Sync Command
            https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
        * Discord.py has tag `?tag usc` which should mirror the link above.
        """
        # Multiple Guilds sync
        if guilds:
            if spec is not None:
                return "`spec` can't be combined with explicit guild IDs."
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
            return f"`{spec}` can only be used inside a guild."

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
                return f"Unknown spec `{spec}`."
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
    async def slash_sync_dev(self, interaction: AluInteraction, spec: SyncSpecLiteral = "global") -> None:
        """🩶 Sync bot's app tree.

        Note that the prefix command can sync multiple guilds, unlike this slash command
        where I only put most commonly used methods of sync.

        Parameters
        ----------
        spec
            Method to sync bot's commands with.
        """
        await interaction.response.defer()
        content = await self.sync_command_worker(spec, current_guild=interaction.guild, guilds=[])
        await interaction.followup.send(content)

    @commands.command(name="sync", hidden=True)
    async def prefix_sync(
        self,
        ctx: AluContext,
        guilds: commands.Greedy[discord.Object],
        spec: SyncSpecLiteral | None = None,
    ) -> None:
        """🩶 Sync bot's app tree.

        Examples
        --------
        * `$sync` or `$sync global` - takes all global commands within the CommandTree and sends them to Discord.
        * `$sync current` - sync all guild commands for the current context's guild.
        * `$sync copy` - copies all global commands to the current guild (within the CommandTree) and syncs.
        * `$sync clear` - remove all guild commands from the CommandTree and syncs,
            which effectively removes all commands from the guild.
        * `$sync 123 456 789` - sync the 3 guild ids we passed: 123, 456 and 789. Only their guilds and guild-bound command.
        """
        content = await self.sync_command_worker(spec, current_guild=ctx.guild, guilds=guilds)
        await ctx.reply(content)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ReloadCog(bot))
