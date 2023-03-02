from .meta import Meta, PrefixSetupCog


async def setup(bot):
    await bot.add_cog(Meta(bot))
    await bot.add_cog(PrefixSetupCog(bot))
