"""New extension.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core import Cog

if TYPE_CHECKING:
    from core import Bot


class NewCog(Cog):
    """NewCog."""


async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(NewCog(bot))
