from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot


class AutoRoleCog(CommunityCog):
    pass


async def setup(bot: AluBot):
    await bot.add_cog(AutoRoleCog(bot))
