"""Control.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands

from core import AluDevCog
from shared import fmt
from utils import const

if TYPE_CHECKING:
    from core import AluBot, AluInteraction

__all__ = ("ControlCog",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# TODO: add errors.Respond when we figure out


class ControlCog(AluDevCog):
    """Control Cog."""

    async def send_logs_worker(self, interaction: AluInteraction, path: str) -> None:
        """Send `.log`.

        Parameters
        ----------
        path
            FIle path to `.log` file.
        """
        await interaction.response.defer()
        await interaction.followup.send(file=discord.File(path))

    async def restart_worker(self, interaction: AluInteraction, project: Literal["alubot", "irebot", "dota2bot"]) -> None:
        """Restart a systemctl based process.

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

    async def journal_worker(self, interaction: AluInteraction, project: Literal["alubot", "irebot", "dota2bot"]) -> None:
        """Journal worker.

        Parameters
        ----------
        project
            Project to get journal for.
        """
        await interaction.response.defer()

        proc = await asyncio.create_subprocess_shell(
            f"sudo journalctl --unit={project} -n 5000 --no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()
        await interaction.followup.send(file=self.bot.transposer.str_to_file(stdout.decode(), f"{project}-journal.log"))

    irebot_group = app_commands.Group(
        name="irebot-dev",
        description="🐬 Control Irebot",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @irebot_group.command(name="logs")
    async def irebot_logs(self, interaction: AluInteraction) -> None:
        """🐬 Get IreBot logs."""
        await self.send_logs_worker(interaction, "../IreBot/.temp/irebot.log")

    @irebot_group.command(name="restart")
    async def irebot_restart(self, interaction: AluInteraction) -> None:
        """🐬 Restart IreBot process."""
        await self.restart_worker(interaction, "irebot")

    @irebot_group.command(name="journal")
    async def irebot_journal(self, interaction: AluInteraction) -> None:
        """🐬 Get IreBot journal."""
        await self.journal_worker(interaction, "irebot")

    alubot_group = app_commands.Group(
        name="alubot-dev",
        description="🦢 Control AluBot",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @alubot_group.command(name="logs")
    async def alubot_logs(self, interaction: AluInteraction) -> None:
        """🦢 Get AluBot logs."""
        await self.send_logs_worker(interaction, ".temp/alubot.log")

    @alubot_group.command(name="restart")
    async def alubot_restart(self, interaction: AluInteraction) -> None:
        """🦢 Restart AluBot process."""
        await self.restart_worker(interaction, "alubot")

    @alubot_group.command(name="journal")
    async def alubot_journal(self, interaction: AluInteraction) -> None:
        """🦢 Get AluBot journal."""
        await self.journal_worker(interaction, "alubot")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ControlCog(bot))
