"""Control.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, override

import discord
from discord import app_commands

from core import AluDevCog
from shared import fmt
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from core import AluBot, AluInteraction

__all__ = ("ControlCog",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class ControlCog(AluDevCog):
    """Control Cog."""

    @override
    async def cog_load(self) -> None:
        self.database_backup.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.database_backup.stop()
        await super().cog_unload()

    #########################################################################################################################
    # DATABASE BACKUP
    #########################################################################################################################

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
            await self.hideout.database.send(file=discord.File(path, filename=path.name))
        finally:
            path.unlink(missing_ok=True)

    #########################################################################################################################
    # PROJECT CONTROL
    #########################################################################################################################

    project_group = app_commands.Group(
        name="project-dev",
        description="🔬 Control Aluerie's projects",
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
    async def project_logs(self, interaction: AluInteraction, project: str) -> None:
        """🔬 Get project's logs."""
        await interaction.response.defer()
        await interaction.followup.send(file=discord.File(project))

    @project_group.command(name="restart")
    @app_commands.choices(project=[app_commands.Choice(name=p, value=p) for p in PROJECTS])
    async def project_restart(self, interaction: AluInteraction, project: str) -> None:
        """🔬 Restart project's process.

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
    async def project_journal(self, interaction: AluInteraction, project: str) -> None:
        """🔬 Get project's journal.

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
        await interaction.followup.send(file=self.bot.transposer.str_to_file(stdout.decode(), f"{project}-journal.log"))


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ControlCog(bot))
