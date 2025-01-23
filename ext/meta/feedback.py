from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import const

if TYPE_CHECKING:
    from bot import AluBot, AluContext

from ._base import MetaCog


class FeedbackModal(discord.ui.Modal, title="Submit Feedback"):
    summary = discord.ui.TextInput(
        label="Summary",
        placeholder="A brief explanation of what you want",
        required=True,
        max_length=const.Limit.Embed.title,
    )
    details = discord.ui.TextInput(
        label="Details",
        placeholder="Write as detailed description as possible...",
        style=discord.TextStyle.long,
        required=True,
        max_length=4000,  # 4000 is max apparently for Views so we can't do Limit.Embed.description,
    )

    def __init__(self, cog: FeedbackCog) -> None:
        super().__init__()
        self.cog: FeedbackCog = cog

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        feedback_channel = self.cog.feedback_channel
        if feedback_channel is None:
            await interaction.response.send_message("Sorry, something went wrong \N{THINKING FACE}", ephemeral=True)
            return
        summary = str(self.summary)
        details = self.details.value

        # Feedback to global logs
        logs_embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title=summary,
                description=details,
                timestamp=interaction.created_at,
            )
            .set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url,
            )
            .set_footer(text=f"Author ID: `{interaction.user.id}`")
        )
        if interaction.guild is not None:
            logs_embed.add_field(
                name="Server",
                value=f"{interaction.guild.name}\nID: `{interaction.guild.id}`",
                inline=False,
            )
        if interaction.channel is not None:
            logs_embed.add_field(
                name="Channel",
                value=f"#{interaction.channel}\nID: `{interaction.channel.id}`",
                inline=False,
            )

        await feedback_channel.send(embed=logs_embed)

        # Success
        success_embed = discord.Embed(
            colour=const.Colour.blueviolet,
            title=summary,
            description=details,
        ).set_author(name="Successfully submitted feedback")
        await interaction.response.send_message(embed=success_embed)

        # Send copy of the embed to the user
        logs_embed.set_footer(
            text=(
                "This copy of your own feedback was sent to you just so "
                "if the developers answer it (here via the bot) - you can remember your previous message."
            ),
        )
        await interaction.user.send(embed=logs_embed)


class FeedbackCog(MetaCog):
    @property
    def feedback_channel(self) -> discord.TextChannel | None:
        return self.bot.hideout.global_logs

    @app_commands.checks.cooldown(1, 5 * 60.0, key=lambda i: i.user.id)
    @app_commands.command()
    async def feedback(self, interaction: discord.Interaction[AluBot]) -> None:
        """🦜 Give feedback about the bot directly to the bot developer."""
        await interaction.response.send_modal(FeedbackModal(self))

    @commands.is_owner()
    @commands.command(aliases=["pm"], hidden=True)
    async def dm(self, ctx: AluContext, user: discord.User, *, content: str) -> None:
        """Write direct message to {user}.

        Meant to be used by the bots developers to contact feedback submitters.
        """
        # dm the user
        embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title="Message from a developer",
                description=content,
            )
            .set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            .set_footer(
                text=(
                    "This message is sent to you in DMs because you had previously submitted feedback or "
                    "I found a bug in a command you used, I do not monitor this DM.\n"
                    "Use `/feedback` again if you *need* to answer my message."
                ),
            )
        )
        await user.send(embed=embed)

        # success message to the bot dev
        embed2 = discord.Embed(
            colour=const.Colour.blueviolet,
            description="DM successfully sent.",
        )
        await ctx.send(embed=embed2)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FeedbackCog(bot))
