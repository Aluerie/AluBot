from utils.const import Emote

from .._base import UtilitiesCog
from .dev_utils import DevUtilities
from .fix_links import LinkUtilities


class Utilities(
    UtilitiesCog,
    DevUtilities,
    LinkUtilities,
    name="Utilities",
    emote=Emote.FeelsDankManLostHisHat,
):
    """
    Utilities
    """


async def setup(bot):
    await bot.add_cog(Utilities(bot))
