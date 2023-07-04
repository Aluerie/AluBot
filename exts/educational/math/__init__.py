from utils.const import Emote

from .._base import EducationalCog
from .wolfram import WolframAlphaCog


class Mathematics(
    WolframAlphaCog,
    EducationalCog,
    emote=Emote.bedNerdge,
):
    """Mathematics"""


async def setup(bot):
    await bot.add_cog(Mathematics(bot))
