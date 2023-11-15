from utils.const import Emote

from .._base import EducationalCog
from .dictionary import DictionaryCog
from .translation import TranslateCog


class Languages(
    TranslateCog,
    DictionaryCog,
    EducationalCog,
    emote=Emote.bedNerdge,
):
    """Languages"""


async def setup(bot):
    await bot.add_cog(Languages(bot))
