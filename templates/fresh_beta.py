# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Template for `ext.beta` extension.

Just copy-paste it there without this docstring.
Then you can beta-test some random code snippets with ease.
"""

from __future__ import annotations

from base_beta import *


class BetaTest(BetaCog):
    async def task_test(self) -> None:  # ty: ignore[missing-override-decorator]
        ...

    @commands.command(name="test", aliases=["beta"])
    async def prefix_test(self, ctx: Context) -> None:
        await ctx.send("test")

    @app_commands.command(name="test")
    async def slash_test(self, interaction: Interaction) -> None:
        await interaction.response.send_message("test")

    async def event_test(self, message: discord.Message) -> None:  # ty: ignore[missing-override-decorator]
        ...


async def setup(bot: Bot) -> None:
    await bot.add_cog(BetaTest(bot))
