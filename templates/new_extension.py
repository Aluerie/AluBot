# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""New extension."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core import Cog

if TYPE_CHECKING:
    from core import Bot


class NewCog(Cog):
    """NewCog."""


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(NewCog(bot))
