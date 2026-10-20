"""Template for `ext.beta` extension.

Just copy-paste it there without this docstring.
Then you can beta-test some random code snippets with ease.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from beta_base import *


class BetaTest(BetaCog):
    async def beta_test_task_count_1(self) -> None:  # ty: ignore[missing-override-decorator]
        pass

    @commands.command(name="test", aliases=["beta"])
    async def test(self, ctx: AluContext) -> None:
        await ctx.send("test")

    @app_commands.command()
    async def slash(self, interaction: AluInteraction) -> None:
        await interaction.response.send_message("slash")


async def setup(bot: AluBot) -> None:
    await bot.add_cog(BetaTest(bot))
