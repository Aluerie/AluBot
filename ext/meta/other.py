from __future__ import annotations

import datetime
import inspect
import itertools
import os
import re
import time
from typing import TYPE_CHECKING, NamedTuple

import aiofiles
import discord
import psutil
import pygit2
from discord import app_commands
from discord.ext import commands
from pygit2.enums import SortMode
from tabulate import tabulate

from bot import AluCog, Url
from utils import const

if TYPE_CHECKING:
    from bot import AluBot


async def count_lines(
    path: str,
    filetype: str = ".py",
    *,
    skip_venv: bool = True,
) -> int:
    lines = 0
    for i in os.scandir(path):
        if i.is_file():
            if i.path.endswith(filetype):
                if skip_venv and re.search(r"(\\|/)?venv(\\|/)", i.path):
                    continue
                lines += len((await (await aiofiles.open(i.path, encoding="utf8")).read()).split("\n"))
        elif i.is_dir():
            lines += await count_lines(i.path, filetype)
    return lines


async def count_others(
    path: str,
    filetype: str = ".py",
    file_contains: str = "def",
    *,
    skip_venv: bool = True,
) -> int:
    line_count = 0
    for i in os.scandir(path):
        if i.is_file():
            if i.path.endswith(filetype):
                if skip_venv and re.search(r"(\\|/)?venv(\\|/)", i.path):
                    continue
                line_count += len(
                    [
                        line
                        for line in (await (await aiofiles.open(i.path, encoding="utf8")).read()).split("\n")
                        if file_contains in line
                    ],
                )
        elif i.is_dir():
            line_count += await count_others(i.path, filetype, file_contains)
    return line_count


def format_commit(commit: pygit2.Commit) -> str:
    short, _, _ = commit.message.partition("\n")
    short = short[0:40] + "..." if len(short) > 40 else short
    short_sha2 = str(commit.id)[0:6]
    commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
    commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)
    offset = discord.utils.format_dt(commit_time, style="R")
    # todo: change the link below to proper global variable I guess ;
    return f"[`{short_sha2}`](https://github.com/Aluerie/AluBot/commit/{commit.id}) {short} ({offset})"


def get_latest_commits(limit: int = 5) -> str:
    repo = pygit2.repository.Repository("./.git")
    commits = list(itertools.islice(repo.walk(repo.head.target, SortMode.TOPOLOGICAL), limit))
    return "\n".join(format_commit(c) for c in commits)


class PingTuple(NamedTuple):
    emoji: str
    name: str
    value: float


class OtherCog(AluCog):
    @app_commands.command()
    async def ping(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{GLOBE WITH MERIDIANS} Checks the bot's ping to Discord and some other services."""
        typing_start = time.monotonic()
        await interaction.response.defer()

        typing_ms = (time.monotonic() - typing_start) * 1000

        start = time.perf_counter()
        message = await interaction.followup.send("\N{TABLE TENNIS PADDLE AND BALL} Pong!", wait=True)
        message_ms = (time.perf_counter() - start) * 1000

        latency_ms = self.bot.latency * 1000

        postgres_start = time.perf_counter()
        await self.bot.pool.fetch("SELECT 1")
        postgres_ms = (time.perf_counter() - postgres_start) * 1000

        pings = [
            ("\N{MEMO}", "Typing", typing_ms),
            ("\N{LOVE LETTER}", "Message", message_ms),
            ("\N{GLOBE WITH MERIDIANS}", "Websocket", latency_ms),
            ("\N{ELEPHANT}", "Database", postgres_ms),
        ]
        average = sum(p[2] for p in pings) / len(pings)
        pings.append(("\N{AVOCADO}", "Average", average))

        table = tabulate(
            tabular_data=pings, headers=(" ", "Ping", "Time, ms"), tablefmt="plain", floatfmt=("g", "g", "07.3f")
        )
        embed = discord.Embed(colour=discord.Colour.dark_embed(), description=f"```py\n{table}\n```")
        await message.edit(embed=embed)

    @app_commands.command()
    async def about(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{GLOBE WITH MERIDIANS} Show information about the bot."""
        await interaction.response.defer()
        information = self.bot.bot_app_info

        embed = (
            discord.Embed(colour=0x9400D3, description=information.description)
            .set_author(name=f"Made by @{information.owner}", icon_url=information.owner.display_avatar.url)
            .add_field(name="Latest updates:", value=get_latest_commits(limit=3), inline=False)
        )

        # statistics
        total_members = 0
        total_unique = len(self.bot.users)
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue
            total_members += guild.member_count or 1

        # avg = [(len([m for m in g.members if not m.bot]) / (g.member_count or 1)) * 100 for g in self.bot.guilds]
        # avg_slash_bot = f"{round(sum(avg) / len(avg), 1)}% avg bot/human"
        embed.add_field(name="Servers", value=f"{guilds} total")  # \n{avg_slash_bot}"
        embed.add_field(name="Members", value=f"{total_members:,} total\n{total_unique:,} unique")

        memory_usage = psutil.Process().memory_full_info().uss / 1024**2
        cpu_usage = psutil.cpu_percent()

        embed.add_field(name="Process", value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU")
        embed.add_field(name="Command Stats", value="*stats coming soon*")
        # todo: implement command run total and total amount of slash/text commands in the bot maybe tasks

        embed.add_field(
            name="Code stats",
            value=(
                f"Lines: {(await count_lines('./', '.py') + await count_lines('./', '.sql')):,}\n"
                f"Functions: {await count_others('./', '.py', 'def '):,}\n"
                f"Classes: {await count_others('./', '.py', 'class '):,}"
            ),
        )
        embed.add_field(name="Last reboot", value=discord.utils.format_dt(self.bot.launch_time, style="R"))
        embed.set_footer(text="Made with Love... and discord.py \N{SPARKLING HEART}", icon_url=const.Logo.Python)
        await interaction.followup.send(embed=embed)

    @app_commands.command()
    async def source(self, interaction: discord.Interaction[AluBot], *, command: str | None = None) -> None:
        """\N{GLOBE WITH MERIDIANS} Links to the bots code, or a specific command's."""
        source_url = interaction.client.repository_url
        branch = "main"

        license_url = f"{source_url}/blob/main/LICENSE"
        embed = (
            discord.Embed(
                colour=0x612783,
                title="Mozilla Public License 2.0",
                url=license_url,
                description=(
                    "\N{BLACK CIRCLE} Remember to follow all license nerdy conditions, "
                    f"especially [this one]({license_url}#L160-L168). Also:"
                ),
            )
            .set_author(name="Code is licensed under MPL v2", url=license_url)
            .set_image(url="https://i.imgur.com/kGFsKcc.png")
        )

        if command is None:
            view = Url(source_url, label="GitHub Repo", emoji=const.EmoteLogo.GitHub)
            await interaction.response.send_message(embed=embed, view=view)
            return

        if command == "help":
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
            obj = "help"
        else:
            obj = self.bot.get_command(command.replace(".", " "))
            if obj is None:
                msg = "Couldn't find source for the command"
                raise commands.BadArgument(msg)

            # since we found the command we're looking for, presumably anyway, let's
            # try to access the code itself
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, first_line_no = inspect.getsourcelines(src)
        if not module.startswith("discord"):
            # not a built-in command
            if filename is None:
                msg = "Couldn't find source for the command"
                raise commands.BadArgument(msg)
            location = os.path.relpath(filename).replace("\\", "/")
        else:
            location = module.replace(".", "/") + ".py"
            source_url = "https://github.com/Rapptz/discord.py"
            branch = "master"

        final_url = f"{source_url}/blob/{branch}/{location}#L{first_line_no}-L{first_line_no + len(lines) - 1}"
        embed.set_footer(text=f"Found source code here:\n{location}#L{first_line_no}-L{first_line_no + len(lines) - 1}")

        view = Url(final_url, label=f'Source code for command "{obj!s}"', emoji=const.EmoteLogo.GitHub)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(OtherCog(bot))
