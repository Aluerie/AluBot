# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Reload All Extensions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands

from core import DevCog
from utils import const

if TYPE_CHECKING:
    from core import Bot, Interaction


class ReloadAllCog(DevCog):
    """Reload All Cog.

    This cog is weirdly isolated from the others just so I can separately include it into my subset of extensions
    to load and it would just give me just one extra command in the discord UI while testing.
    """

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="reload-all")
    async def reload_all(self, interaction: Interaction) -> None:
        """🧩 Reload every loaded extension."""
        await interaction.response.defer(ephemeral=True)
        failed: list[str] = []
        for ext in list(self.bot.extensions):
            # if ext == __name__:
            #     continue
            try:
                await self.bot.reload_extension(ext)
            except commands.ExtensionError as e:
                failed.append(f"`{ext}`: {e}")
        message = "❌ Failed to reload:\n" + "\n".join(failed) if failed else "✅ Reloaded all extensions"
        await interaction.followup.send(message[:2000])


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(ReloadAllCog(bot))
