from utils import AluBot, const

from .._category import FPCCog
from .notifs import DotaNotifs
from .postmatch import DotaPostMatchEdit
from .settings import DotaNotifsSettings
from .twitch_check import DotaTwitchAccountCheck


class Dota2FPC(
    FPCCog,
    DotaNotifs,
    DotaPostMatchEdit,
    DotaNotifsSettings,
    DotaTwitchAccountCheck,
    emote=const.Emote.DankLove,
):
    """
    Dota 2 - Favourite player+character combo notifications.
    """


async def setup(bot: AluBot):
    await bot.add_cog(Dota2FPC(bot))
