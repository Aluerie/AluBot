"""HELP COMMAND."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands

from bot import AluCog

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class HelpCommandCog(AluCog):
    """A cog defining `/help` slash command.

    Some advice against having help slash command, but I think help menu allows
    for a better categorical presentation than current UI menu does.
    If Discord makes it better in future - I will gladly remove this cog.
    """

    @app_commands.command()
    async def help(self, interaction: AluInteraction) -> None:
        """Shows all bot's commands and features."""
        await interaction.response.send_message("xd")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(HelpCommandCog(bot))
