from .wolfram import WolframAlphaCog

from utils.const import Emote

from .._base import EducationalCog


class Mathematics(
    WolframAlphaCog,
    EducationalCog,
    emote=Emote.bedNerdge,
):
    """Mathematics"""


async def setup(bot):
    await bot.add_cog(Mathematics(bot))
