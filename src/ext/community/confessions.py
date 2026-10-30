# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Confessions."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self, override

import discord
from discord.ext import commands

from core import Cog, Modal, View
from utils import const

if TYPE_CHECKING:
    from core import Bot, Context, Interaction


SAINT_MESSAGE = (
    f"{const.Emoji.bubuChrist} {const.Emoji.bubuChrist} {const.Emoji.bubuChrist} "
    "\N{CHURCH} \N{CHURCH} \N{CHURCH} "
    f"{const.Emoji.PepoBeliever} {const.Emoji.PepoBeliever} {const.Emoji.PepoBeliever}"
)


class ConfessionModal(Modal):
    """Modal to make a confession."""

    text = discord.ui.TextInput(
        label="Make confession to the server",
        style=discord.TextStyle.long,
        placeholder="Type your confession text here (max 4000 characters)",
        max_length=4000,
    )

    def __init__(self, *, anonymous: bool) -> None:
        super().__init__(title="Anonymous confession" if anonymous else "Non-anonymous confession")
        self.anonymous = anonymous

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Confessions only work in text channels.", ephemeral=True)
            return
        await interaction.response.send_message(f"The Lord be with you {const.Emoji.PepoBeliever}", ephemeral=True)

        embed = discord.Embed(title=self.title, color=0x9678B6, description=self.text.value)
        if not self.anonymous:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

        await channel.send(embed=embed)
        await channel.send(SAINT_MESSAGE)

        if interaction.message:
            try:
                await interaction.message.delete()
            except discord.NotFound:
                return  # someone else already reposted the menu
        await channel.send(view=MakeConfessionButtons())


class MakeConfessionButtons(View):
    """View with buttons to make confessions."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Anonymous confession",
        custom_id="anonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=str(const.Emoji.bubuChrist),
    )
    async def anonymous_confession(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Make an anonymous confession."""
        await interaction.response.send_modal(ConfessionModal(anonymous=True))

    @discord.ui.button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=str(const.Emoji.PepoBeliever),
    )
    async def non_anonymous_confession(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Make a non-anonymous confession."""
        await interaction.response.send_modal(ConfessionModal(anonymous=False))


class Confessions(Cog):
    """Community Confessions.

    Members can confess their sins to the community.
    Confessions can be anonymous/non-anonymous.
    """

    @override
    async def cog_load(self) -> None:
        """Register a view for persistent listening."""
        self.bot.add_view(MakeConfessionButtons())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def new_confession_buttons(self, ctx: Context) -> None:
        """Create a view with anonymous/non-anonymous confession buttons.

        Ideally, this should only be used once to setup the confession menu.
        """
        await ctx.send(view=MakeConfessionButtons())
        await asyncio.sleep(2.0)
        await ctx.message.delete()


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Confessions(bot))
