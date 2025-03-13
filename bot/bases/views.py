"""Custom View subclasses.

This module provides
* AluView class - subclass of discord.ui.View
* AluModal class - subclass of discord.ui.Modal
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord

from utils import const, errors, fmt, helpers

if TYPE_CHECKING:
    from .context import AluInteraction

__all__ = (
    "AluModal",
    "AluView",
    "Url",
)


async def on_views_modals_error(
    view: discord.ui.View,
    interaction: AluInteraction,
    error: Exception,
    item: discord.ui.Item[discord.ui.View] | None = None,
) -> None:
    """Handler called when an error is raised within an AluView or AluModal objects.

    Basically, error handler for views and modals.
    """
    # error handler variables
    desc: str = "No description"
    is_unexpected: bool = False

    if isinstance(error, errors.AluBotError):
        desc = str(error)
    else:
        # error is unexpected
        is_unexpected = True

        args_join = f"[view]: {view}" + (f"\n[item]: {item}" if item else "")
        snowflake_ids = (
            f"author  = {interaction.user.id}\n"  # comment to prevent formatting from concatenating the lines
            f"channel = {interaction.channel_id}\n"  # so I can see the alignment better
            f"guild   = {interaction.guild_id}"
        )

        metadata_embed = (
            discord.Embed(color=0x2A0553, title=f"Error in View: `{view.__class__.__name__}`")
            .set_author(
                name=(
                    f"@{interaction.user} in #{interaction.channel} "
                    f"({interaction.guild.name if interaction.guild else 'DM Channel'})"
                ),
                icon_url=interaction.user.display_avatar,
            )
            .add_field(name="View Objects", value=fmt.code(args_join, "ps"), inline=False)
            .add_field(name="Snowflake IDs", value=fmt.code(snowflake_ids, "ebnf"), inline=False)
            .set_footer(
                text=f"{view.__class__.__name__}.on_error",
                icon_url=interaction.guild.icon if interaction.guild else interaction.user.display_avatar,
            )
        )

        await interaction.client.exc_manager.register_error(error, metadata_embed, interaction.channel_id)
        if interaction.channel_id == interaction.client.hideout.spam_channel_id:
            # we don't need any extra embeds;
            if not interaction.response.is_done():
                await interaction.response.send_message(":(", ephemeral=True)
            return

    response_to_user_embed = helpers.error_handler_response_embed(error, desc, unexpected=is_unexpected)
    if interaction.response.is_done():
        await interaction.followup.send(embed=response_to_user_embed)
    else:
        await interaction.response.send_message(embed=response_to_user_embed)


class AluView(discord.ui.View):
    """Subclass for discord.ui.View.

    All view elements used in AluBot should subclass this class when using views.
    Because this class provides universal features like error handler.

    Parameters
    ----------
    author_id: int | None
        Author of the Interactive View . The bot will disallow other people to interact with elements of this View.
        If `None` then everybody is allowed to do so.
    view_name: str, optional
        _description_, by default "Interactive Element"

    """

    if TYPE_CHECKING:
        message: discord.Message | discord.WebhookMessage
        """Note that technically this attribute might not exist because we manually assign it after sending the message.
        Therefore check for `hasattr(self, "message")` when needed.
        """

    def __init_subclass__(cls, name: str = "Interactive Element") -> None:
        cls.name: str = name
        """Essentially a display name for the View, which is shown to the end-user in some cases.

        We can try doing __class__.__name__ stuff and add spaces instead of "Interactive Element",
        but it might get tricky since like FPCSetupMiscView exists
        """
        return super().__init_subclass__()

    def __init__(
        self,
        *,
        author_id: int | None,
        timeout: float | None = 180.0,
    ) -> None:
        """Initialize AluView."""
        super().__init__(timeout=timeout)
        self.author_id: int | None = author_id

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        """Interaction check that blocks non-authors from clicking view items."""
        if self.author_id is None:
            # we allow this view to be controlled by everybody
            return True
        if interaction.user.id == self.author_id:
            # we allow this view to be controlled only by interaction author
            return True
        # we need to deny control to this non-author user
        embed = discord.Embed(
            color=const.Color.error,
            description=f"Sorry! This `{self.name}` is not meant for you.",
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
                item.disabled = True  # type: ignore[reportAttributeAccessIssue]
            await self.message.edit(view=self)

    @override
    async def on_error(
        self, interaction: AluInteraction, error: Exception, item: discord.ui.Item[discord.ui.View]
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
    async def on_error(self, interaction: AluInteraction, error: Exception) -> None:
        await on_views_modals_error(self, interaction, error)
