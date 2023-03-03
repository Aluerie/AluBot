from .notifs import DotaNotifs
from .postmatch import DotaPostMatchEdit
from .settings import DotaNotifsSettings
from .twitch_check import DotaTwitchAccountCheck

DOTA_COGS = (
    DotaNotifs,
    DotaPostMatchEdit,
    DotaNotifsSettings,
    DotaTwitchAccountCheck,
)


async def setup(bot):
    for C in DOTA_COGS:
        await bot.add_cog(C(bot))
