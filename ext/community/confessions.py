from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, override

import discord
from discord.ext import commands

from bot import AluModal, AluView
from utils import const, fmt

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


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
        await interaction.response.send_message(
            content=f"The Lord be with you {const.Emote.PepoBeliever}", ephemeral=True
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
        # retry_after = self.cd.update_rate_limit(ntr) # returns retry_after which is nice
        bucket = cd.get_bucket(interaction)
        if bucket and (retry_after := bucket.get_retry_after()):
            raise ButtonOnCooldown(retry_after)
        return True

    @override
    async def on_error(
        self,
        interaction: discord.Interaction[AluBot],
        error: Exception,
        item: discord.ui.Item[Self],
    ) -> None:
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
    async def button0_callback(self, interaction: AluInteraction, button: discord.ui.Button[Self]) -> None:
        await interaction.response.send_modal(ConfessionModal(title=button.label))

    @discord.ui.button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=const.Emote.PepoBeliever,
    )
    async def button1_callback(self, interaction: AluInteraction, button: discord.ui.Button[Self]) -> None:
        await interaction.response.send_modal(ConfessionModal(title=button.label))


class Confession(CommunityCog):
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(ConfessionView())  # Registers a View for persistent listening

        # very silly testing way
        # print('hello')
        # await self.bot.get_channel(Channel.spam_me).send(view=ConfView())


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Confession(bot))
