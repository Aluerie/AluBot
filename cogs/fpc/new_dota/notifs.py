from __future__ import annotations

from typing import TYPE_CHECKING

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluBot

class DotaNotifs(AluCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)


async def setup(bot: AluBot):
    await bot.add_cog(DotaNotifs(bot))