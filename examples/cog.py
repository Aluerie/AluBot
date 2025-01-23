from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import BaseCog

if TYPE_CHECKING:
    from bot import AluBot


class MyCog(BaseCog): ...


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(MyCog(bot))
