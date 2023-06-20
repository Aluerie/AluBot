from utils.const import Emote

from .dev_utils import DevUtilities
from .fix_links import LinkUtilities
from .tools import ToolsCog
from .wolfram import WolframAlpha


class Utilities(
    DevUtilities,
    LinkUtilities,
    ToolsCog,
    WolframAlpha,
    name='Utilities',
    emote=Emote.FeelsDankManLostHisHat
):
    """
    Utilities
    """


async def setup(bot):
    await bot.add_cog(Utilities(bot))
