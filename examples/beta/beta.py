from __future__ import annotations

from examples.beta.base import *


class BetaTestCog(BetaCog, name='BetaTest'):
    @aluloop(count=1)
    async def beta_task(self):
        pass

    @commands.command()
    async def ceta(self, ctx: AluContext):
        await ctx.send('ceta')

    @commands.hybrid_command()
    async def heta(self, ctx: AluContext):
        await ctx.send('heta')

    @app_commands.command()
    async def seta(self, ntr: discord.Interaction[AluBot]):
        await ntr.response.send_message('seta')


async def setup(bot: AluBot):
    await bot.add_cog(BetaTestCog(bot))
