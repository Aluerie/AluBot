from .integration import Integration


async def setup(bot):
    await bot.add_cog(Integration(bot))