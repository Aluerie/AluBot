"""Custom View subclasses.

This module provides
* AluView class - subclass of discord.ui.View
* AluModal class - subclass of discord.ui.Modal
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord

from utils import const, errors, helpers

if TYPE_CHECKING:
    from bot import AluBot

__all__ = (
    "AluModal",
    "AluView",
    "Url",
)


async def on_views_modals_error(
    view: discord.ui.View,
    interaction: discord.Interaction[AluBot],
    error: Exception,
    item: discord.ui.Item[discord.ui.View] | None = None,
) -> None:
    """Handler called when an error is raised within an AluView or AluModal objects.

    Basically, error handler for views and modals.
    """
    # error handler variables
    desc: str = "No description"
    is_unexpected: bool = False
    mention = True

    if isinstance(error, errors.AluBotError):
        desc = str(error)
    else:
        # error is unexpected
        is_unexpected = True

        metadata_embed = (
            discord.Embed(colour=0x2A0553, title="Error in View")
            .add_field(
                name="View Objects",
                value=(f"```py\n[view]: {view}" + (f"\n[item]: {item}" if item else "") + "```"),
            )
            .add_field(
                name="Snowflake Ids",
                value=(
                    "```py\n"
                    f"author  = {interaction.user.id}\n"
                    f"channel = {interaction.channel_id}\n"
                    f"guild   = {interaction.guild_id}```"
                ),
                inline=False,
            )
            .set_author(
                name=(
                    f"@{interaction.user} in #{interaction.channel} "
                    f"({interaction.guild.name if interaction.guild else "DM Channel"})"
                ),
                icon_url=interaction.user.display_avatar,
            )
            .set_footer(
                text=f"on_views_modals_error: {view.__class__.__name__}",
                icon_url=interaction.guild.icon if interaction.guild else interaction.user.display_avatar,
            )
        )

        mention = interaction.channel_id != interaction.client.hideout.spam_channel_id
        await interaction.client.exc_manager.register_error(error, metadata_embed, mention=mention)

    response_to_user_embed = helpers.error_handler_response_embed(error, is_unexpected, desc, mention)

    if interaction.response.is_done():
        await interaction.followup.send(embed=response_to_user_embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=response_to_user_embed, ephemeral=True)


class AluView(discord.ui.View):
    """Subclass for discord.ui.View.

    All view elements used in AluBot should subclass this class when using views.
    Because this class provides universal features like error handler.

    Parameters
    ----------
    author_id : int | None
        _description_
    timeout : float | None
        _description_, by default 5*60.0
    view_name : str, optional
        _description_, by default "Interactive Element"

    """

    if TYPE_CHECKING:
        message: discord.Message | discord.InteractionMessage

    def __init__(
        self,
        *,
        author_id: int | None,
        view_name: str = "Interactive Element",
        timeout: float | None = 5 * 60.0,
    ) -> None:
        """Initialize AluView."""
        super().__init__(timeout=timeout)
        self.author_id: int | None = author_id

        # we could try doing __class__.__name__ stuff and add spaces, replace "view" with "interactive element"
        # but it might get tricky since like FPCSetupMiscView exists
        self.view_name: str = view_name

    @override
    async def interaction_check(self, interaction: discord.Interaction[AluBot]) -> bool:
        """Interaction check that blocks non-authors from clicking view items."""
        if self.author_id is None:
            # we allow this view to be controlled by everybody
            return True
        if interaction.user.id == self.author_id:
            # we allow this view to be controlled only by interaction author
            return True
        # we need to deny control to this non-author user
        embed = discord.Embed(
            colour=const.Colour.maroon,
            description=f"Sorry! This {self.view_name} is not meant to be controlled by you.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    @override
    async def on_timeout(self) -> None:
        """On timeout we disable items in view so they are not clickable any longer if possible.

        Requires us to assign message object to view so it can edit the message.
        """
        if hasattr(self, "message"):
            for item in self.children:
                # item in self.children is Select/Button which have ``.disable`` but typehinted as Item
                item.disabled = True  # type: ignore
            await self.message.edit(view=self)

    @override
    async def on_error(
        self, interaction: discord.Interaction[AluBot], error: Exception, item: discord.ui.Item[discord.ui.View],
    ) -> None:
        """My own Error Handler for Views."""
        await on_views_modals_error(self, interaction, error, item)


class Url(discord.ui.View):
    """Lazy class to make URL button in one line instead of two."""

    def __init__(self, url: str, label: str = "Open", emoji: str | None = None) -> None:
        """Initialize Url object."""
        super().__init__()
        self.add_item(discord.ui.Button(label=label, emoji=emoji, url=url))


class AluModal(discord.ui.Modal):
    """Subclass for discord.ui.Modal.

    Provides an error handler.
    """

    @override
    async def on_error(self, interaction: discord.Interaction[AluBot], error: Exception) -> None:
        await on_views_modals_error(self, interaction, error)
