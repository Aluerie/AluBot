# ruff: noqa: D100, D101, D102, D103, T200, T201, F841
# pyright: reportImplicitOverride=false
from __future__ import annotations

from examples.beta.base import *


class BetaTest(BetaCog):
    @aluloop(count=1)
    async def beta_task(self) -> None:
        pass

    @app_commands.command()
    async def slash(self, interaction: AluInteraction) -> None:
        await interaction.response.send_message("slash")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(BetaTest(bot))
