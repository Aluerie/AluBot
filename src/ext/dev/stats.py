"""Stats.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from core import AluContext, AluDevCog

if TYPE_CHECKING:
    from core import AluBot


class StatsCog(AluDevCog):
    """Stats Cog."""

    @commands.command(name="invite-link")
    async def invite_link(self, ctx: AluContext) -> None:
        """Get invite link for the bot.

        Somewhat pointless since 'Add App' button exists.
        But it's useful to have for @YenBot where I removed that button.
        """
        await ctx.send(self.bot.invite_link)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(StatsCog(bot))
