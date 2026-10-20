"""Meta.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from tabulate import tabulate

from core import AluCog, AluInteraction
from shared import clock, fmt, gh
from utils import cache, const

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from core import AluBot


async def _timed_ping(awaitable: Awaitable[object]) -> float | None:
    """Return how long awaitable took in ms, or `None` on failure or timeout."""
    start = time.perf_counter()
    try:
        async with asyncio.timeout(5):
            await awaitable
    except Exception:  # ruff: ignore[blind-except]
        return None
    return (time.perf_counter() - start) * 1000


def _cell(value: float | None) -> str:
    """Format cells in /ping."""
    return "N/A" if value is None else f"{value:.3f}"


class Meta(AluCog):
    """Meta."""

    botinfo_group = app_commands.Group(  # apparently, `bot_group` is not allowed
        name="bot",
        description="🌐 Information about the bot.",
        allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=True),
    )

    @botinfo_group.command()
    async def ping(self, interaction: AluInteraction) -> None:
        """🌐 Check the bot's ping to Discord and some other services."""
        interaction_ping = await _timed_ping(interaction.response.defer())
        content = "🏓 Pong!"
        (
            message_ping,
            postgres_ping,
        ) = await asyncio.gather(
            _timed_ping(interaction.followup.send(content, wait=True)),  # `wait=True` so we get proper `message_ping`
            _timed_ping(self.bot.pool.fetchval("SELECT 1")),
        )

        latency = self.bot.latency * 1000
        websocket_ping = None if math.isnan(latency) or math.isinf(latency) else latency

        table = tabulate(
            tabular_data=[
                ("📝", "Interaction", _cell(interaction_ping)),
                ("💌", "Message", _cell(message_ping)),
                ("🌐", "Websocket", _cell(websocket_ping)),
                ("🐘", "Database", _cell(postgres_ping)),
            ],
            headers=(" ", "Ping", "Time, ms"),
            tablefmt="plain",
            colalign=("left", "left", "right"),
            # floatfmt=("g", "g", "07.3f"),
            disable_numparse=True,  # values are pre-formatted by `_cell`
        )
        new_content = f"{content}\n{fmt.codeblock(table)}"
        await interaction.edit_original_response(content=new_content)

    @cache.cache()
    async def _latest_commits_markdown(self) -> str:
        """Latest commits markdown."""
        commits = await asyncio.to_thread(gh.get_latest_commits, limit=5)
        return "\n".join(
            f"* [`{c.short_sha2}`]({self.bot.repository_url}/commit/{c.id}) "
            f"{c.emojified_title} {clock.discord(c.utc_dt, 'R')}"
            for c in commits
        )

    @cache.cache()
    async def _code_stats_field_value(self) -> str:
        """Code stats field value."""
        lines, funcs, classes = await asyncio.gather(
            gh.LinesCounter("./", (".py", ".sql")).count(),
            gh.ContainsCounter("./", ".py", "def ").count(),
            gh.ContainsCounter("./", ".py", "class ").count(),
        )
        return f"Lines: {lines:,}\nFunctions: {funcs:,}\nClasses: {classes:,}"

    @botinfo_group.command()
    async def source(self, interaction: AluInteraction) -> None:
        """🌐 Show GitHub repository link, latest updates and some code stats."""
        await interaction.response.defer()
        bot_app_info = self.bot.bot_app_info
        commits, stats = await asyncio.gather(self._latest_commits_markdown(), self._code_stats_field_value())
        await interaction.followup.send(
            embed=(
                discord
                .Embed(
                    color=0x9400D3,
                    description=(
                        f"{const.Emote.GitHub}Source: {self.bot.repository_url}\n"
                        f"## {const.Emote.GitHub} Latest updates\n{commits}"
                    ),
                )
                .set_author(
                    name=f"Made by {bot_app_info.owner.display_name} (@{bot_app_info.owner})",
                    icon_url=bot_app_info.owner.display_avatar.url,
                )
                .add_field(name="Code stats", value=stats)
                .set_footer(text="Made with love... ❤", icon_url=self.bot.user.display_avatar)
            )
        )


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Meta(bot))
