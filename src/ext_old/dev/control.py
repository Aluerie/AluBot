from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, override

import discord
import psutil
from discord import app_commands

from core import aluloop
from utils import const

from ._base import BaseDevCog

if TYPE_CHECKING:
    from core import AluBot, AluInteraction

__all__ = ("Control",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Control(BaseDevCog):
    """Utilities for system-wide control and information for AluBot and some other projects of mine."""

    @override
    async def cog_load(self) -> None:
        self.database_backup.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.database_backup.stop()
        await super().cog_unload()

    @aluloop(time=datetime.time(hour=18, minute=5, tzinfo=datetime.UTC))
    async def database_backup(self) -> None:
        """Daily task to backup the bot's database.

        Sends pg_dump into my private discord server.
        Which is not secure, I guess, but for now it's fine.
        """
        if self.bot.is_vps:
            await asyncio.create_subprocess_shell("pg_dump alubot > .temp/alubot.sql")
            await asyncio.sleep(10)  # wait till pg_dump finished dumping (otherwise next line will send 0 bytes empty file)
            await self.hideout.database.send(file=discord.File(fp=".temp/alubot.sql", filename="alubot.sql"))

    system_group = app_commands.Group(
        name="system-dev",  # TODO: maybe rename this to alubot-dev so it matches irebot-dev :thinking:
        description="(#Hideout) commands for bot's system-wide control.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    async def send_logs_helper(self, interaction: AluInteraction, path: str) -> None:
        """Helper function to send project logs as a file with a command.

        Parameters
        ----------
        interaction: AluInteraction
            Application Command Interaction that was triggered by the command.
        path: str
            FIle path to `.log` file.
        """
        await interaction.response.defer()
        await interaction.followup.send(file=discord.File(path))

    async def restart_helper(self, interaction: AluInteraction, project: Literal["alubot", "irebot"]) -> None:
        """Restart a systemctl based process on VPS.

        Usable to restart the bot (or other projects) without logging to VPS machine or committing something.
        Sometimes, it's just more comfortable to do it from discord window or mobile.
        """
        await interaction.response.send_message("Rebooting in 3 2 1")
        await asyncio.sleep(3)
        try:
            # non systemctl users - sorry
            await asyncio.create_subprocess_shell(f"sudo systemctl restart {project}")
        except Exception:
            log.exception("Failed to restart %s", project, stack_info=True)
            # it might not go off
            await interaction.followup.send("Something went wrong.")

    @system_group.command(name="logs")
    async def system_logs(self, interaction: AluInteraction) -> None:
        """🔬 Get AluBot's logs."""
        await self.send_logs_helper(interaction, ".temp/alubot.log")

    @system_group.command(name="restart")
    async def system_restart(self, interaction: AluInteraction) -> None:
        """🔬 Restart AluBot process on VPS."""
        await self.restart_helper(interaction, "alubot")

    irebot_group = app_commands.Group(
        name="irebot-dev",
        description="(#Hideout) commands for irebot's control.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @irebot_group.command(name="logs")
    async def irebot_logs(self, interaction: AluInteraction) -> None:
        """🔬 Get IreBot logs."""
        await self.send_logs_helper(interaction, "../IreBot/.temp/irebot.log")

    @irebot_group.command(name="restart")
    async def irebot_restart(self, interaction: AluInteraction) -> None:
        """🔬 Restart IreBot process on VPS."""
        await self.restart_helper(interaction, "irebot")

    @irebot_group.command(name="journal")
    async def irebot_journal(self, interaction: AluInteraction) -> None:
        """🔬 Get IreBot journal."""
        await interaction.response.defer()

        proc = await asyncio.create_subprocess_shell(
            "sudo journalctl --unit=irebot -n 5000 --no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()

        await interaction.followup.send(
            file=self.bot.transposer.str_to_file(
                stdout.decode(),
                "irebot-journal.log",
            )
        )


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Control(bot))
