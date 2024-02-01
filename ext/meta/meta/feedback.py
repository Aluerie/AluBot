from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import const

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

from .._base import MetaCog


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

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = self.cog.feedback_channel
        if channel is None:
            await interaction.response.send_message("Sorry, something went wrong \N{THINKING FACE}", ephemeral=True)
            return

        summary, details = str(self.summary), self.details.value
        # feedback to global logs
        e = self.cog.get_feedback_embed(interaction, summary=summary, details=details)
        await channel.send(embed=e)
        # success
        e2 = self.cog.get_successfully_submitted_embed(summary=summary, details=details)
        await interaction.response.send_message(embed=e2)
        # send copy of the embed to the user
        e3 = self.cog.get_feedback_copy_embed(summary=summary, details=details)
        await interaction.user.send(embed=e3)


class FeedbackCog(MetaCog):
    @property
    def feedback_channel(self) -> discord.TextChannel | None:
        # maybe add different channel
        return self.bot.hideout.global_logs

    @staticmethod
    def get_feedback_copy_embed(
        summary: str = "No feedback title was provided (prefix?)",
        details: str = "No feedback details were provided",
    ) -> discord.Embed:
        e = discord.Embed(title=summary, description=details, colour=const.Colour.blueviolet)

        e.set_footer(
            text=(
                "This copy of your own feedback was sent to you just so "
                "if the developers answer it (here via the bot) - you can remember your previous message."
            )
        )
        return e

    @staticmethod
    def get_feedback_embed(
        ctx_ntr: AluContext | discord.Interaction,
        *,
        summary: str = "No feedback title was provided (prefix?)",
        details: str = "No feedback details were provided",
    ) -> discord.Embed:
        embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title=summary,
                description=details,
                timestamp=ctx_ntr.created_at,
            )
            .set_author(name=str(ctx_ntr.user), icon_url=ctx_ntr.user.display_avatar.url)
            .set_footer(text=f"Author ID: `{ctx_ntr.user.id}`")
        )

        if ctx_ntr.guild is not None:
            embed.add_field(name="Server", value=f"{ctx_ntr.guild.name}\nID: `{ctx_ntr.guild.id}`", inline=False)

        if ctx_ntr.channel is not None:
            embed.add_field(name="Channel", value=f"#{ctx_ntr.channel}\nID: `{ctx_ntr.channel.id}`", inline=False)

        return embed

    @staticmethod
    def get_successfully_submitted_embed(
        summary: str | None = None,
        details: str | None = None,
    ) -> discord.Embed:
        e = discord.Embed(colour=const.Colour.blueviolet, title=summary, description=details)
        e.set_author(name="Successfully submitted feedback")
        return e

    @commands.command(name="feedback")
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def prefix_feedback(self, ctx: AluContext, *, details: str) -> None:
        """Give feedback about the bot directly to the bot developer.

        This is a quick way to request features or bug fixes. \
        The bot will DM you about the status of your request if possible/needed.
        You can also open issues/PR on [GitHub](https://github.com/Aluerie/AluBot).
        """

        channel = self.feedback_channel
        if channel is None:
            await ctx.reply("Sorry, something went wrong \N{THINKING FACE}", ephemeral=True)
            return

        e = self.get_feedback_embed(ctx, details=details)
        await channel.send(embed=e)
        e2 = self.get_successfully_submitted_embed(details=details)
        await ctx.send(embed=e2)
        # send copy of the embed to the user
        e3 = self.get_feedback_copy_embed(details=details)
        await ctx.author.send(embed=e3)

    @app_commands.command(name="feedback")
    async def slash_feedback(self, interaction: discord.Interaction) -> None:
        """Give feedback about the bot directly to the bot developer."""
        await interaction.response.send_modal(FeedbackModal(self))

    @commands.is_owner()
    @commands.command(aliases=["pm"], hidden=True)
    async def dm(self, ctx: AluContext, user: discord.User, *, content: str) -> None:
        """Write direct message to {user}.

        Meant to be used by the bots developers to contact feedback submitters.
        """

        # dm the user
        e = discord.Embed(colour=const.Colour.blueviolet, title="Message from a developer")
        e.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        e.description = content
        footer_text = (
            "This message is sent to you in DMs because you had previously submitted feedback or "
            "I found a bug in a command you used, I do not monitor this DM.\n"
            "Use `/feedback` again if you *need* to answer my message."
        )
        e.set_footer(text=footer_text)
        await user.send(embed=e)

        # success message to the bot dev
        e2 = discord.Embed(colour=const.Colour.blueviolet, description="DM successfully sent.")
        await ctx.send(embed=e2)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(FeedbackCog(bot))
