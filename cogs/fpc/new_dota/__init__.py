from .notifs import DotaNotifs

DOTA_COGS = (DotaNotifs,)


async def setup(bot):
    for C in DOTA_COGS:
        await bot.add_cog(C(bot))
