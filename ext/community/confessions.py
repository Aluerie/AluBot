from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Self, override

import discord
from discord.ext import commands

from bot import AluCog, AluModal, AluView
from utils import const, fmt

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext, AluInteraction


__all__ = ("Confessions",)


class ButtonOnCooldown(commands.CommandError):
    def __init__(self, retry_after: float) -> None:
        self.retry_after: float = retry_after


def key(interaction: AluInteraction) -> discord.User | discord.Member:
    return interaction.user


# rate of 1 token per 30 minutes using our key function
cd = commands.CooldownMapping.from_cooldown(1.0, 30.0 * 60, key)


class ConfessionModal(AluModal):
    """Modal to make a confession."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    conf = discord.ui.TextInput(
        label="Make confession to the server",
        style=discord.TextStyle.long,
        placeholder="Type your confession text here",
        max_length=4000,
    )

    @override
    async def on_submit(self, interaction: AluInteraction) -> None:
        embed = discord.Embed(title=self.title, color=const.Color.prpl, description=self.conf.value)
        if self.title == "Non-anonymous confession":
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        channel = interaction.channel
        assert isinstance(channel, discord.TextChannel)

        await channel.send(embeds=[embed])
        saint_string = (
            f"{const.Emote.bubuChrist} {const.Emote.bubuChrist} {const.Emote.bubuChrist} "
            "\N{CHURCH} \N{CHURCH} \N{CHURCH} "
            f"{const.Emote.PepoBeliever} {const.Emote.PepoBeliever} {const.Emote.PepoBeliever}"
        )
        await channel.send(saint_string)
        await interaction.response.send_message(content=f"The Lord be with you {const.Emote.PepoBeliever}", ephemeral=True)
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
        emoji=const.Emote.bubuChrist,
    )
    async def anonymous_confession(self, interaction: AluInteraction, button: discord.ui.Button[Self]) -> None:
        """Make an anonymous confession."""
        await interaction.response.send_modal(ConfessionModal(title=button.label))

    @discord.ui.button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=const.Emote.PepoBeliever,
    )
    async def non_anonymous_confession(self, interaction: AluInteraction, button: discord.ui.Button[Self]) -> None:
        """Make a non-anonymous confession."""
        await interaction.response.send_modal(ConfessionModal(title=button.label))


class Confessions(AluCog):
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


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Confessions(bot))
