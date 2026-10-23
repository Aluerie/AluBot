"""Uncategorized.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core import Cog

if TYPE_CHECKING:
    from core import AluBot


class UncategorizedCog(Cog):
    """Uncategorized Cog."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(UncategorizedCog(bot))
