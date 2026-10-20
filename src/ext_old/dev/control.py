from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, override

import discord
from discord import app_commands

from core import aluloop
from utils import const

from ._base import BaseDevCog

if TYPE_CHECKING:
    from core import AluBot

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


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Control(bot))
