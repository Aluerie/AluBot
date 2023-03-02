from .notifs import DotaNotifs
from .postmatch import DotaPostMatchEdit
from .settings import DotaNotifsSettings
from .twitch_check import DotaTwitchAccountCheck


async def setup(bot):
    await bot.add_cog(DotaNotifs(bot))
    await bot.add_cog(DotaPostMatchEdit(bot))
    await bot.add_cog(DotaNotifsSettings(bot))
    await bot.add_cog(DotaTwitchAccountCheck(bot))
