from __future__ import annotations

import platform
import socket
from typing import TYPE_CHECKING

import discord
import pkg_resources
import psutil
from discord.ext import commands

from utils import checks, const

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class DevInformation(DevBaseCog):
    @checks.app.is_hideout()
    @commands.hybrid_group(name="system", hidden=True)
    async def system(self, ctx: AluContext):
        """Group command for /system subcommands."""
        await ctx.send_help()

    @system.command(name="information", aliases=["info"])
    async def system_information(self, ctx: AluContext):
        """(\N{GREY HEART} Hideout-Only) Get system info about machine hosting the bot."""

        embed = (
            discord.Embed(
                colour=const.Colour.prpl(),
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
                    f"\N{BLACK CIRCLE} CPU usage: \n{psutil.cpu_percent()}% | {psutil.cpu_freq().current / 1000:.1f}GHz\n"
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
        await ctx.reply(embed=embed)

    @system.command(name="packages")
    async def system_packages(self, ctx: AluContext):
        """(\N{GREY HEART} Hideout-Only) Get info bot's main Python Packages."""
        curious_packages = [
            "discord.py",
            "twitchio",
            "steam",
            "dota2",
            "pulsefire",
        ]  # list of packages versions of which I'm interested the most

        embed = discord.Embed(
            colour=const.Colour.prpl(),
            title="List of bot's Main Packages",
            description="\n".join(
                f"\N{BLACK CIRCLE} {package}: {pkg_resources.get_distribution(package).version}"
                for package in curious_packages
            ),
        )
        await ctx.reply(embed=embed)


async def setup(bot: AluBot):
    await bot.add_cog(DevInformation(bot))
