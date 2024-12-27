from __future__ import annotations

import asyncio
import importlib
import importlib.metadata
import logging
import os
import platform
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import discord
import psutil
from discord import app_commands

from utils import const

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class DevInformation(DevBaseCog):
    system_group = app_commands.Group(
        name="system",
        description="(#Hideout) commands for bot's system-wide information or operation commands.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @system_group.command(name="restart")
    async def system_restart(self, interaction: discord.Interaction[AluBot]) -> None:
        """🔬 (#Hideout) Restart the bot process on VPS.

        Usable to restart the bot without logging to VPS machine or committing something.
        """
        await interaction.response.send_message("Rebooting in 3 2 1")
        await asyncio.sleep(3)
        try:
            # non systemctl users - sorry
            os.system("sudo systemctl restart alubot")
        except Exception as error:
            log.error(error, stack_info=True)
            # it might not go off
            await interaction.followup.send("Something went wrong.")

    @system_group.command(name="information")
    async def system_information(self, interaction: discord.Interaction[AluBot]) -> None:
        """🔬 (#Hideout) Get system info about machine hosting the bot."""
        # some data doesn't fit nicely with chained embed initialization format
        cpu_freq = f"| {ghz.current / 1000:.1f}GHz\n" if (ghz := psutil.cpu_freq()) else ""

        embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title="Bot Host Machine System Info",
                description=(
                    f"\N{BLACK CIRCLE} Hostname: {socket.gethostname()}\n"
                    f"\N{BLACK CIRCLE} Machine: {platform.machine()}\n"
                    f"\N{BLACK CIRCLE} Platform: {platform.platform()}\n"
                    f"\N{BLACK CIRCLE} System: `{platform.system()}` release: `{platform.release()}`\n"
                    f"\N{BLACK CIRCLE} Version: `{platform.version()}`\n"
                    f"\N{BLACK CIRCLE} Processor: {platform.processor()}\n"
                ),
            )
            .add_field(
                name="Current % | max values",
                value=(
                    f"\N{BLACK CIRCLE} CPU usage: \n{psutil.cpu_percent()}% {cpu_freq}"
                    f"\N{BLACK CIRCLE} RAM usage: \n{psutil.virtual_memory().percent}% | "
                    f'{str(round(psutil.virtual_memory().total / (1024.0 ** 3))) + " GB"}\n'
                    f'\N{BLACK CIRCLE} Disk usage: \n{(du := psutil.disk_usage("/")).percent} % | '
                    f"{du.used / (1024 ** 3):.1f}GB/{du.total / (1024 ** 3):.1f}GB"
                ),
            )
            .set_footer(text=f"AluBot is a copyright 2020-{discord.utils.utcnow().year} of {self.bot.owner.name}")
        )

        if not self.bot.test:
            # Sorry, I don't want to randomly dox myself on test bot :D
            async with self.bot.session.get("https://ipinfo.io/json") as resp:
                if resp.ok:
                    ip_data = await resp.json()
                    location_string = f"· {ip_data['country']} {ip_data['region']} {ip_data['city']}"
                else:
                    location_string = "Sorry! Couldn't fetch the data"
            embed.add_field(name="Bot's Location judging by IP", value=location_string)
        await interaction.response.send_message(embed=embed)

    @system_group.command(name="packages")
    async def system_packages(self, interaction: discord.Interaction[AluBot]) -> None:
        """🔬 (#Hideout) Get info bot's main Python Packages."""
        curious_packages = [
            "discord.py",
            "twitchio",
            "steam",  # VALVE_SWITCH
            # "dota2",
            "pulsefire",
        ]  # list of packages versions of which I'm interested the most
        pv = sys.version_info  # python version

        embed = (
            discord.Embed(colour=const.Colour.blueviolet)
            .add_field(
                name="Python Version",
                value=f"{pv.major}.{pv.minor}.{pv.micro} {pv.releaselevel} {pv.serial}",  # cspell: ignore releaselevel
            )
            .add_field(
                name="List of bot's Main Packages",
                value="\n".join(
                    f"\N{BLACK CIRCLE} {package}: {importlib.metadata.version(package)}" for package in curious_packages
                ),
            )
        )
        await interaction.response.send_message(embed=embed)

    @system_group.command(name="logs")
    async def system_logs(self, interaction: discord.Interaction[AluBot]) -> None:
        """🔬 (#Hideout) Get bot's logs."""
        await interaction.response.defer()
        await interaction.followup.send(file=discord.File(".temp/alubot.log"))

    @system_group.command(name="health")
    async def system_health(self, interaction: discord.Interaction[AluBot]) -> None:
        """🔬 (#Hideout) Get bot's health status."""
        await interaction.response.defer()

        # todo: customize this to my liking.

        # This uses a lot of private methods because there is no
        # clean way of doing this otherwise.

        HEALTHY = discord.Colour(value=0x43B581)  # noqa: N806
        UNHEALTHY = discord.Colour(value=0xF04947)  # noqa: N806
        discord.Colour(value=0xF09E47)
        total_warnings = 0

        embed = discord.Embed(title="Bot Health Report", colour=HEALTHY)

        # Check the connection pool health.
        pool = self.bot.pool
        total_waiting = len(pool._queue._getters)
        current_generation = pool._generation

        description = [
            f"Total `Pool.acquire` Waiters: {total_waiting}",
            f"Current Pool Generation: {current_generation}",
            f"Connections In Use: {len(pool._holders) - pool._queue.qsize()}",
        ]

        questionable_connections = 0
        connection_value = []
        for index, holder in enumerate(pool._holders, start=1):
            generation = holder._generation
            in_use = holder._in_use is not None
            is_closed = holder._con is None or holder._con.is_closed()
            display = f"gen={holder._generation} in_use={in_use} closed={is_closed}"
            questionable_connections += any((in_use, generation != current_generation))
            connection_value.append(f"<Holder i={index} {display}>")

        joined_value = "\n".join(connection_value)
        embed.add_field(name="Connections", value=f"```py\n{joined_value}\n```", inline=False)

        all_tasks = asyncio.all_tasks(loop=self.bot.loop)
        event_tasks = [t for t in all_tasks if "Client._run_event" in repr(t) and not t.done()]

        cogs_directory = Path(__file__).parent
        tasks_directory = Path("discord") / "ext" / "tasks" / "__init__.py"
        inner_tasks = [t for t in all_tasks if str(cogs_directory) in repr(t) or str(tasks_directory) in repr(t)]

        bad_inner_tasks = ", ".join(hex(id(t)) for t in inner_tasks if t.done() and t._exception is not None)
        total_warnings += bool(bad_inner_tasks)
        embed.add_field(name="Inner Tasks", value=f'Total: {len(inner_tasks)}\nFailed: {bad_inner_tasks or "None"}')
        embed.add_field(name="Events Waiting", value=f"Total: {len(event_tasks)}", inline=False)

        process = psutil.Process()
        memory_usage = f"{process.memory_full_info().uss / 1024**2:.2f} MiB"
        cpu_usage = f"{process.cpu_percent() / cpu_count:.2f} % CPU" if (cpu_count := psutil.cpu_count()) else ""
        embed.add_field(name="Process", value=f"{memory_usage}\n{cpu_usage}", inline=False)

        global_rate_limit = not self.bot.http._global_over.is_set()
        description.append(f"Global Rate Limit: {global_rate_limit}")

        if global_rate_limit or total_warnings >= 9:
            embed.colour = UNHEALTHY

        embed.set_footer(text=f"{total_warnings} warning(s)")
        embed.description = "\n".join(description)
        await interaction.followup.send(embed=embed)

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command(name="logs")
    async def logs(
        self,
        interaction: discord.Interaction[AluBot],
        project: Literal["AluBot", "LueBot", "Gloria"],
    ) -> None:
        """(\N{GREY HEART} Hideout-Only) Get project's logs.

        Parameters
        ----------
        project
            Project to fetch `.log` file for.
        """
        await interaction.response.defer()
        mapping = {
            "AluBot": ".alubot/.temp/alubot.log",
            "LueBot": "../LueBot/.temp/irenesbot.log",
            "Gloria": "../Gloria/.steam.log",
        }
        await interaction.followup.send(file=discord.File(mapping[project]))


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DevInformation(bot))
