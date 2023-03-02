from .owner import AdminTools


async def setup(bot):
    await bot.add_cog(AdminTools(bot))
