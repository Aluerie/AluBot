"""Stats.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core import DevCog
from utils import const

if TYPE_CHECKING:
    from core import AluBot, Context


class StatsCog(DevCog):
    """Stats Cog."""

    JAILED_BOTS_ROLE_ID = 1090428532162822234

    @commands.command(name="invite-link")
    async def invite_link(self, ctx: Context) -> None:
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
        if member.guild.id != const.Guild.hideout:
            return

        if member.bot:
            await member.add_roles(
                discord.Object(self.JAILED_BOTS_ROLE_ID), reason="New bot account: jailed by default"
            )
        else:
            await self.bot.notify_developers(
                f"{member} ({member.id}) joined and I'm kicking them. Please disable invites."
            )
            await member.kick(reason="Non-bot account joined hideout (it's private)")


async def setup(bot: AluBot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(StatsCog(bot))
