"""Confessions.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self, override

import discord
from discord import ui
from discord.ext import commands

from core import Cog, UiMixin
from shared import fmt
from utils import const

if TYPE_CHECKING:
    from core import Bot, Interaction


SAINT_MESSAGE = (
    f"{const.Emoji.bubuChrist} {const.Emoji.bubuChrist} {const.Emoji.bubuChrist} "
    "\N{CHURCH} \N{CHURCH} \N{CHURCH} "
    f"{const.Emoji.PepoBeliever} {const.Emoji.PepoBeliever} {const.Emoji.PepoBeliever}"
)


class ButtonOnCooldown(commands.CommandError):
    def __init__(self, retry_after: float) -> None:
        self.retry_after: float = retry_after


def key(interaction: Interaction) -> discord.User | discord.Member:
    return interaction.user


# rate of 1 token per 30 minutes using our key function
cd = commands.CooldownMapping.from_cooldown(1.0, 30.0 * 60, key)


class ConfessionModal(UiMixin, ui.Modal):
    """Modal to make a confession."""

    anonymous = ui.RadioGroup(
        options=[
            discord.RadioGroupOption(
                label="Anonymous confession",
                value="anon",
                description="People will not see who posted the confession.",
            ),
            discord.RadioGroupOption(
                label="Non-anonymous confession",
                value="non-anon",
                description="People will see your name + profile picture attached to the confession.",
            ),
        ]
    )

    conf = discord.ui.TextInput(
        label="Make confession to the server",
        style=discord.TextStyle.long,
        placeholder="Type your confession text here",
        max_length=4000,
    )

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        embed = discord.Embed(title=self.title, color=0x9678B6, description=self.conf.value)
        if self.anonymous.value == "non-anon":
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.channel
        assert isinstance(channel, discord.TextChannel)

        await channel.send(embeds=[embed])

        await channel.send(SAINT_MESSAGE)
        await interaction.response.send_message(
            content=f"The Lord be with you {const.Emoji.PepoBeliever}", ephemeral=True
        )
        if interaction.message:
            await interaction.message.delete()
        await channel.send(view=ConfessionView())
        cd.update_rate_limit(interaction)


class ConfessionView(AluView):
    """View with buttons to make confessions."""

    def __init__(self) -> None:
        super().__init__(author_id=None, timeout=None)

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        retry_after = cd.update_rate_limit(interaction)
        if retry_after:
            raise ButtonOnCooldown(retry_after)
        return True

    @override
    async def on_error(self, interaction: AluInteraction, error: Exception, item: discord.ui.Item[Self]) -> None:
        if isinstance(error, ButtonOnCooldown):
            msg = f"Sorry, you are on cooldown \nTime left `{fmt.human_timedelta(error.retry_after, mode='brief')}`"
            embed = discord.Embed(color=const.Color.error, description=msg).set_author(name=error.__class__.__name__)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await super().on_error(interaction, error, item)

    @discord.ui.button(
        label="Anonymous confession",
        custom_id="anonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=str(const.Emoji.bubuChrist),
    )
    async def anonymous_confession(self, interaction: Interaction, button: discord.ui.Button[Self]) -> None:
        """Make an anonymous confession."""
        await interaction.response.send_modal(ConfessionModal(title=button.label))

    @discord.ui.button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=str(const.Emoji.PepoBeliever),
    )
    async def non_anonymous_confession(self, interaction: AluInteraction, button: discord.ui.Button[Self]) -> None:
        """Make a non-anonymous confession."""
        await interaction.response.send_modal(ConfessionModal(title=button.label))


class Confessions(Cog):
    """Community Confessions.

    Members can confess their sins to the community.
    Confessions can be anonymous/non-anonymous.
    """

    @commands.Cog.listener(name="on_ready")
    async def activate_confessions(self) -> None:
        """Register a view for persistent listening."""
        self.bot.add_view(ConfessionView())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def new_confession_buttons(self, ctx: AluGuildContext) -> None:
        """Create a view with anonymous/non-anonymous confession buttons.

        Ideally, this should only be used once to setup the confession menu.
        """
        await ctx.send(view=ConfessionView())
        await asyncio.sleep(2.0)
        await ctx.message.delete()


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Confessions(bot))
