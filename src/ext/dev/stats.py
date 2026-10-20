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
    import discord

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

    @commands.Cog.listener(name="on_member_join")
    async def moderate_hideout_joiners(self, member: discord.Member) -> None:
        """Jail or kick outsiders.

        * Kicks non-bot accounts from the server if they somehow managed to enter;
        * Gives newly entered bot-accounts @Jailed Bots role.
        """
        if member.guild.id != self.hideout.guild.id:
            return

        if member.bot:
            await member.add_roles(self.hideout.jailed_bots_role, reason="New bot account: jailed by default")
        else:
            await self.hideout.repost.send(f"{member} ({member.id}) joined and I'm kicking them. Please disable invites.")
            await member.kick(reason="Non-bot account joined hideout (it's private)")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(StatsCog(bot))
