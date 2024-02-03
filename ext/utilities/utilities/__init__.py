from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .._base import UtilitiesCog
from .dev_utils import DevUtilities
from .fix_links import LinkUtilities

if TYPE_CHECKING:
    from bot import AluBot


class Utilities(
    UtilitiesCog,
    DevUtilities,
    LinkUtilities,
    name="Utilities",
    emote=Emote.FeelsDankManLostHisHat,
):
    """Utilities
    """


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Utilities(bot))
