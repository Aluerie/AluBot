from __future__ import annotations

from examples.beta.base import *

# pyright: basic


class BetaTest(BetaCog):
    @aluloop(count=1)
    async def beta_task(self) -> None:
        pass

    @commands.command()
    async def prefix(self, ctx: AluContext) -> None:
        await ctx.send("prefix")

    @commands.hybrid_command()
    async def hybrid(self, ctx: AluContext) -> None:
        await ctx.send("hybrid")

    @app_commands.command()
    async def slash(self, interaction: discord.Interaction[AluBot]) -> None:
        await interaction.response.send_message("slash")


async def setup(bot: AluBot) -> None:
    await bot.add_cog(BetaTest(bot))
